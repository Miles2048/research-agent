import os
from loguru import logger

from .tools_and_schemas import SearchQueryList, Reflection
from dotenv import load_dotenv
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.types import Send
from langgraph.graph import StateGraph
from langgraph.graph import START, END
from langchain_core.runnables import RunnableConfig
import json
import requests
from typing import List, Dict, Any

# LangSmith integration
from langsmith import traceable

from .state import (
    OverallState,
    QueryGenerationState,
    ReflectionState,
    WebSearchState,
)
from .configuration import Configuration
from .prompts import (
    get_current_date,
    query_writer_instructions,
    web_searcher_instructions,
    reflection_instructions,
    answer_instructions,
    source_summary_instructions,
    related_content_extraction_instructions,
)
from langchain_openai import ChatOpenAI
from .utils import (
    get_citations,
    get_research_topic,
    insert_citation_markers,
    resolve_urls,
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

if os.getenv("OPENAI_API_KEY") is None:
    raise ValueError("OPENAI_API_KEY is not set")


# Nodes
@traceable(name="generate_query")
def generate_query(state: OverallState, config: RunnableConfig) -> QueryGenerationState:
    """LangGraph node that generates search queries based on the User's question.

    Uses chatGPT 4o-mini to create an optimized search queries for web research based on
    the User's question.

    Args:
        state: Current graph state containing the User's question
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated queries
    """
    configurable = Configuration.from_runnable_config(config)

    # check for custom initial search query count
    if state.get("initial_search_query_count") is None:
        state["initial_search_query_count"] = configurable.number_of_initial_queries

    # init OpenAI model
    llm = ChatOpenAI(
        model=configurable.query_generator_model,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    structured_llm = llm.with_structured_output(SearchQueryList)

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = query_writer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        number_queries=state["initial_search_query_count"],
    )
    # Generate the search queries;Extend queries method
    result = structured_llm.invoke(formatted_prompt)
    return {"search_query": result.query}


def continue_to_web_research(state: QueryGenerationState):
    """LangGraph node that sends the search queries to the web research node.

    This is used to spawn n number of web research nodes, one for each search query.
    """
    return [
        Send("web_research", {"search_query": search_query, "id": int(idx)})
        for idx, search_query in enumerate(state["search_query"])
    ]

@traceable(name="web_research")
def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs web research using OpenAI with web search integration.

    Executes a web search and uses OpenAI to analyze and summarize the results.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    # Configure
    configurable = Configuration.from_runnable_config(config)
    search_query = state["search_query"]
    
    # Perform web search
    # TODO 
    search_results = perform_web_search(search_query)
    
    # Use OpenAI to analyze and summarize the search results
    llm = ChatOpenAI(
        model=configurable.query_generator_model,
        temperature=0,
        max_retries=2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    # Format the prompt with search results
    search_context = "\n\n".join([
        f"Title: {result['title']}\nURL: {result['url']}\nSnippet: {result['snippet']}"
        for result in search_results[:5]  # Use top 5 results
    ])
    
    # prompt for summarize 
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=search_query,
    ) + f"\n\nSearch Results:\n{search_context}\n\nBased on these search results, provide a comprehensive summary with citations."
    
    # Get OpenAI response
    response = llm.invoke(formatted_prompt)
    
    # Create sources from search results
    sources_gathered = [
        {
            "title": result["title"],
            "url": result["url"],
            "snippet": result["snippet"],
            "full_text": result.get("full_text", ""),  # Include full text
            "short_url": f"https://search.result/{state['id']}-{i}",
            "value": result["url"],
            "label": result["title"][:50] + "..." if len(result["title"]) > 50 else result["title"],
            "summary": "",  # Initialize summary field
            "related_content": "",  # Initialize related_content field
            "verified": False  # Initialize verified field
        }
        for i, result in enumerate(search_results[:5])
    ]
    
    # Generate summaries and extract related content for each source
    logger.info(f"开始为 {len(sources_gathered)} 个数据源生成摘要和提取相关内容")
    successful_summaries = 0
    successful_extractions = 0
    
    for source in sources_gathered:
        try:
            # Generate summary
            summary = generate_source_summary(source["title"], source["snippet"])
            source["summary"] = summary
            if summary:
                successful_summaries += 1
        except Exception as e:
            logger.warning(f"摘要生成失败: {source['title'][:30]}... - {str(e)}")
            source["summary"] = ""
        
        try:
            # Extract related content
            related_content = extract_related_content(source["title"], source["snippet"])
            source["related_content"] = related_content
            if related_content:
                successful_extractions += 1
        except Exception as e:
            logger.warning(f"内容提取失败: {source['title'][:30]}... - {str(e)}")
            source["related_content"] = ""
    
    logger.info(f"处理完成: {successful_summaries}/{len(sources_gathered)} 个摘要成功, {successful_extractions}/{len(sources_gathered)} 个内容提取成功")
    
    # Add citations to the response
    modified_text = response.content
    for i, source in enumerate(sources_gathered):
        if i == 0:  # Add citation to the end of the response
            modified_text += f"\n\nSources:\n"
        modified_text += f"[{source['label']}]({source['url']})\n"

    return {
        "sources_gathered": sources_gathered,
        "search_query": [state["search_query"]],
        "web_research_result": [modified_text],
    }


# @traceable(name="web_research")
# def web_research(state: WebSearchState, config: RunnableConfig) -> OverallState:
    """LangGraph node that performs research using both web search and knowledge base.

    Uses OpenAI with bound tools to intelligently search both web and local knowledge base.

    Args:
        state: Current graph state containing the search query and research loop count
        config: Configuration for the runnable, including search API settings

    Returns:
        Dictionary with state update, including sources_gathered, research_loop_count, and web_research_results
    """
    # Configure
    configurable = Configuration.from_runnable_config(config)
    search_query = state["search_query"]

    # Initialize LLM
    llm = ChatOpenAI(
        model=configurable.query_generator_model,
        temperature=0,
        max_retries=2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    
    # Import tools
    try:
        from .tools_and_schemas import web_search, knowledge_search
        tools_available = True
        logger.info("Successfully imported search tools")
    except ImportError as e:
        logger.error(f"Failed to import search tools: {str(e)}")
        tools_available = False
    
    
    
    # Format the initial prompt
    formatted_prompt = web_searcher_instructions.format(
        current_date=get_current_date(),
        research_topic=search_query,
    )
    
    # Initialize variables
    all_sources = []
    web_research_results = []
    
    if tools_available:
        # Use tool-based approach similar to agent1
        logger.info(f"Starting tool-based research for: {search_query}")
        
        llm_with_tools = llm.bind_tools([web_search, knowledge_search])
        
        # Initialize messages
        # TODO 现在这个prompt效果差，需迭代
        messages = [HumanMessage(content=formatted_prompt)]
        
        # Multi-turn tool calling loop
        
        max_iterations = 5  # Prevent infinite loops
        iteration = 0
        
        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Tool calling iteration {iteration}")
            
            # Get LLM response
            response = llm_with_tools.invoke(messages)
            messages.append(response)
            
            # Check if LLM wants to use tools
            if response.tool_calls:
                logger.info(f"LLM requested {len(response.tool_calls)} tool calls")
                
                for tool_call in response.tool_calls:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    logger.info(f"Calling tool: {tool_name} with args: {tool_args}")
                    
                    try:
                        # Execute the tool
                        if tool_name == "web_search":
                            results = web_search.invoke(tool_args)
                        elif tool_name == "knowledge_search":
                            results = knowledge_search.invoke(tool_args)
                        else:
                            logger.warning(f"Unknown tool: {tool_name}")
                            results = []
                        
                        # Process results
                        if results:
                            logger.info(f"{tool_name} returned {len(results)} results")
                            
                            # Add to sources with proper formatting
                            for i, result in enumerate(results):
                                # Ensure consistent format
                                source = {
                                    "title": result.get("title", ""),
                                    "url": result.get("url", ""),
                                    "snippet": result.get("snippet", ""),
                                    "short_url": f"https://search.result/{state['id']}-{len(all_sources)+i}",
                                    "value": result.get("url", ""),
                                    "label": result.get("title", "")[:50] + "..." if len(result.get("title", "")) > 50 else result.get("title", ""),
                                    "summary": result.get("summary", ""),
                                    "related_content": result.get("full_text", "")[:50000] if result.get("full_text") else "",
                                    "verified": result.get("verified", False),
                                    # TODO 对接一下还需要什么字段
                                    # TODO 对接一下需不需要这个字段source_type
                                    "source_type": result.get("source_type", "unknown")
                                }
                                all_sources.append(source)
                            
                            # Create tool message with results
                            tool_message = ToolMessage(
                                content=f"Found {len(results)} results from {tool_name}",
                                tool_call_id=tool_call["id"]
                            )
                            messages.append(tool_message)
                            
                            # Add detailed results to web research results
                            result_text = f"\n{tool_name} results:\n"
                            for result in results[:3]:  # Top 3 for brevity
                                result_text += f"- {result.get('title', 'No title')}: {result.get('snippet', '')[:200]}...\n"
                            web_research_results.append(result_text)
                        else:
                            logger.info(f"{tool_name} returned no results")
                            tool_message = ToolMessage(
                                content=f"No results found from {tool_name}",
                                tool_call_id=tool_call["id"]
                            )
                            messages.append(tool_message)
                            
                    except Exception as e:
                        logger.error(f"Error calling {tool_name}: {str(e)}")
                        tool_message = ToolMessage(
                            content=f"Error calling {tool_name}: {str(e)}",
                            tool_call_id=tool_call["id"]
                        )
                        messages.append(tool_message)
            else:
                # No more tool calls, LLM is done
                logger.info("LLM finished tool calling")
                web_research_results.append(response.content)
                break
        
        # If no sources were found, fall back to direct web search
        # TODO 这个等prompt优化好，要删掉，llm应该能自己决策
        if not all_sources:
            logger.warning("No sources found via tools, falling back to direct search")
            search_results = perform_web_search(search_query)
            all_sources = [
                {
                    "title": result["title"],
                    "url": result["url"],
                    "snippet": result["snippet"],
                    "full_text": result.get("full_text", ""),  # Include full text
                    "short_url": f"https://search.result/{state['id']}-{i}",
                    "value": result["url"],
                    "label": result["title"][:50] + "..." if len(result["title"]) > 50 else result["title"],
                    "summary": "",
                    "related_content": "",
                    "verified": False,
                    "source_type": "web"
                }
                for i, result in enumerate(search_results[:5])
            ]
            
    else:
        # Fallback to original implementation
        logger.info("Tools not available, using direct web search")
        search_results = perform_web_search(search_query)
        
        # Use original processing logic
        search_context = "\n\n".join([
            f"Title: {result['title']}\nURL: {result['url']}\nSnippet: {result['snippet']}"
            for result in search_results[:5]
        ])
        
        formatted_prompt += f"\n\nSearch Results:\n{search_context}\n\nBased on these search results, provide a comprehensive summary with citations."
        response = llm.invoke(formatted_prompt)
        web_research_results.append(response.content)
        
        all_sources = [
            {
                "title": result["title"],
                "url": result["url"],
                "snippet": result["snippet"],
                "full_text": result.get("full_text", ""),  # Include full text
                "short_url": f"https://search.result/{state['id']}-{i}",
                "value": result["url"],
                "label": result["title"][:50] + "..." if len(result["title"]) > 50 else result["title"],
                "summary": "",
                "related_content": "",
                "verified": False,
                "source_type": "web"
            }
            for i, result in enumerate(search_results[:5])
        ]
    
    # Generate summaries for sources that don't have them
    logger.info(f"Processing {len(all_sources)} total sources")
    for source in all_sources:
        if not source.get("summary") and source.get("snippet"):
            try:
                summary = generate_source_summary(source["title"], source["snippet"])
                source["summary"] = summary
            except Exception as e:
                logger.warning(f"Failed to generate summary: {str(e)}")
                source["summary"] = ""
    
    # Combine all research results
    final_result = "\n\n".join(web_research_results)
    
    # Add source citations
    if all_sources:
        final_result += "\n\nSources:\n"
        for source in all_sources:
            final_result += f"[{source['label']}]({source['url']}) - {source['source_type']}\n"
    
    logger.info(f"Research completed with {len(all_sources)} sources")
    
    return {
        "sources_gathered": all_sources,
        "search_query": [state["search_query"]],
        "web_research_result": [final_result],
    }


@traceable(name="perform_web_search")
def perform_web_search(query: str, num_results: int = 5) -> List[Dict]:
    """执行网络搜索，优先使用Exa API，如果失败则回退到模拟搜索。
    
    Args:
        query: 搜索查询字符串
        num_results: 返回结果数量
        
    Returns:
        包含标题、URL和摘要的搜索结果列表
    """
    from .tools.exa_search import perform_exa_search
    
    try:
        # 使用Exa API进行搜索
        results = perform_exa_search(query, num_results=num_results)
        if results:
            logger.info(f"Exa搜索成功: {len(results)} 个结果")
            return results
    except Exception as e:
        logger.warning("Exa搜索失败，使用模拟搜索")
    
    # 后备: 模拟搜索结果用于开发和测试
    logger.info("使用模拟搜索结果")
    return [
        {
            "title": f"搜索结果 {i+1}: {query}",
            "url": f"https://example.com/result-{i+1}",
            "snippet": f"这是查询'{query}'的模拟搜索结果。实际结果将包含相关信息。"
        }
        for i in range(num_results)
    ]


@traceable(name="generate_source_summary")
def generate_source_summary(title: str, content: str) -> str:
    """为数据源生成摘要
    
    Args:
        title: 数据源标题
        content: 数据源内容
        
    Returns:
        str: 生成的摘要，失败时返回空字符串
    """
    try:
        # 检查输入是否为空
        if not title or not content:
            logger.warning("标题或内容为空，跳过摘要生成")
            return ""
        
        # 限制内容长度以控制成本和提高性能
        max_content_length = 500
        truncated_content = content[:max_content_length] if len(content) > max_content_length else content
        
        # 初始化 OpenAI 模型，使用 gpt-4o-mini
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.3,
            max_tokens=150,
            timeout=5.0,
            max_retries=1,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        # 格式化提示词
        formatted_prompt = source_summary_instructions.format(
            title=title,
            content=truncated_content
        )
        
        # 生成摘要
        response = llm.invoke(formatted_prompt)
        summary = response.content.strip()
        
        if summary:
            logger.debug(f"source_summary生成成功: {title[:30]}...")
            return summary
        else:
            logger.warning(f"source_summary生成返回空内容: {title[:30]}...")
            return ""
            
    except Exception as e:
        logger.warning(f"摘要生成失败 '{title[:30]}...': {str(e)}")
        return ""


@traceable(name="extract_related_content")
def extract_related_content(title: str, content: str) -> str:
    """从数据源中提取最相关的内容片段
    
    Args:
        title: 数据源标题
        content: 数据源内容
        
    Returns:
        str: 提取的原文片段，失败时返回空字符串
    """
    try:
        # 检查输入是否为空
        if not title or not content:
            logger.warning("标题或内容为空，跳过内容提取")
            return ""
        
        # 限制内容长度以控制成本和提高性能
        max_content_length = 1000  # 比摘要更长，因为需要提取更多内容
        truncated_content = content[:max_content_length] if len(content) > max_content_length else content
        
        # 初始化 OpenAI 模型，使用 gpt-4o-mini
        llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0.1,  
            max_tokens=400,   
            timeout=5.0,      # 5秒超时
            max_retries=1,
            api_key=os.getenv("OPENAI_API_KEY"),
        )
        
        # 格式化提示词
        formatted_prompt = related_content_extraction_instructions.format(
            title=title,
            content=truncated_content
        )
        
        # 提取相关内容
        response = llm.invoke(formatted_prompt)
        related_content = response.content.strip()
        
        if related_content:
            logger.debug(f"related_content提取成功: {title[:30]}...")
            return related_content
        else:
            logger.warning(f"related_content提取返回空内容: {title[:30]}...")
            return ""
            
    except Exception as e:
        logger.warning(f"内容提取失败 '{title[:30]}...': {str(e)}")
        return ""


@traceable(name="reflection")
def reflection(state: OverallState, config: RunnableConfig) -> ReflectionState:
    """LangGraph node that identifies knowledge gaps and generates potential follow-up queries.

    Analyzes the current summary to identify areas for further research and generates
    potential follow-up queries. Uses structured output to extract
    the follow-up query in JSON format.

    Args:
        state: Current graph state containing the running summary and research topic
        config: Configuration for the runnable, including LLM provider settings

    Returns:
        Dictionary with state update, including search_query key containing the generated follow-up query
    """
    configurable = Configuration.from_runnable_config(config)
    # Increment the research loop count and get the reasoning model
    state["research_loop_count"] = state.get("research_loop_count", 0) + 1
    reasoning_model = state.get("reasoning_model", configurable.reflection_model)

    # Format the prompt;about conditional edge
    current_date = get_current_date()
    formatted_prompt = reflection_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n\n---\n\n".join(state["web_research_result"]),
    )
    # init OpenAI Reasoning Model
    llm = ChatOpenAI(
        model=reasoning_model,
        temperature=1.0,
        max_retries=2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    result = llm.with_structured_output(Reflection).invoke(formatted_prompt)

    return {
        "is_sufficient": result.is_sufficient,
        "knowledge_gap": result.knowledge_gap,
        "follow_up_queries": result.follow_up_queries, # instead of call generate_queries
        "research_loop_count": state["research_loop_count"],
        "number_of_ran_queries": len(state["search_query"]),
    }


def evaluate_research(
    state: ReflectionState,
    config: RunnableConfig,
) -> OverallState:
    """LangGraph routing function that determines the next step in the research flow.

    Controls the research loop by deciding whether to continue gathering information
    or to finalize the summary based on the configured maximum number of research loops.

    Args:
        state: Current graph state containing the research loop count
        config: Configuration for the runnable, including max_research_loops setting

    Returns:
        String literal indicating the next node to visit ("web_research" or "finalize_summary")
    """
    configurable = Configuration.from_runnable_config(config)
    max_research_loops = (
        state.get("max_research_loops")
        if state.get("max_research_loops") is not None
        else configurable.max_research_loops
    )
    if state["is_sufficient"] or state["research_loop_count"] >= max_research_loops:
        return "finalize_answer"
    else:
        return [
            Send(
                "web_research",
                {
                    "search_query": follow_up_query,
                    "id": state["number_of_ran_queries"] + int(idx),
                },
            )
            for idx, follow_up_query in enumerate(state["follow_up_queries"])
        ]


@traceable(name="finalize_answer")
def finalize_answer(state: OverallState, config: RunnableConfig):
    """LangGraph node that finalizes the research summary and saves results to files.

    Prepares the final output by deduplicating and formatting sources, then
    combining them with the running summary to create a well-structured
    research report with proper citations. Also saves the report and sources to local files.

    Args:
        state: Current graph state containing the running summary and sources gathered

    Returns:
        Dictionary with state update, including messages, sources, and saved file paths
    """
    from datetime import datetime
    from .tools.file_tools import save_report, save_source_data, create_summary_file
    
    configurable = Configuration.from_runnable_config(config)
    reasoning_model = state.get("reasoning_model") or configurable.answer_model

    # Format the prompt
    current_date = get_current_date()
    formatted_prompt = answer_instructions.format(
        current_date=current_date,
        research_topic=get_research_topic(state["messages"]),
        summaries="\n---\n\n".join(state["web_research_result"]),
    )

    # TODO: claude
    # init OpenAI Model for final answer
    llm = ChatOpenAI(
        model=reasoning_model,
        temperature=0,
        max_retries=2,
        api_key=os.getenv("OPENAI_API_KEY"),
    )
    result = llm.invoke(formatted_prompt)

    # Replace the short urls with the original urls and collect unique sources
    unique_sources = []
    seen_urls = set()  # 用于跟踪已经添加的URL
    
    for source in state["sources_gathered"]:
        # 替换短链接为真实URL
        if source["short_url"] in result.content:
            result.content = result.content.replace(
                source["short_url"], source["value"]
            )
        
        # 根据URL去重，只添加未见过的数据源
        source_url = source.get("value", source.get("url", ""))
        if source_url and source_url not in seen_urls:
            unique_sources.append(source)
            seen_urls.add(source_url)
    
    logger.info(f"研究完成，收集到 {len(unique_sources)} 个唯一数据源（去重前: {len(state['sources_gathered'])} 个）")

    # 保存研究报告和数据源到文件
    query = get_research_topic(state["messages"])
    
    # 准备元数据
    metadata = {
        "timestamp": datetime.now().isoformat(),
        "model": reasoning_model,
        "search_queries": state.get("search_query", []),
        "sources_count": len(unique_sources)
    }
    
    # 保存报告 - 使用配置的路径和文件名
    custom_output_dir = configurable.output_dir or "result"
    custom_source_dir = configurable.source_data_dir or "result/source_data"
    
    report_path = save_report(
        report_content=result.content,
        query=query,
        metadata=metadata,
        output_dir=custom_output_dir,
        custom_filename=configurable.report_filename
    )
    
    # 从数据库获取评分信息并添加到sources中
    try:
        from .tools.database import DatabaseManager
        db_manager = DatabaseManager()
        
        logger.info("开始获取数据源的评分信息...")
        updated_sources = 0
        
        # 为每个源查询并添加评分信息
        for source in unique_sources:
            source_url = source.get("value", source.get("url", ""))
            if source_url:
                logger.info(f"🔍 正在查询URL评分: {source_url}")
                
                # 查询数据库获取评分信息
                evaluation_data = db_manager.get_evaluation_by_url(source_url)
                
                if evaluation_data:
                    logger.info(f"✅ 找到评分数据: {evaluation_data}")
                    logger.info(f"📝 更新前source keys: {list(source.keys())}")
                    source.update(evaluation_data)
                    updated_sources += 1
                    logger.info(f"📝 已更新评分信息: {source.get('title', 'Unknown')[:30]}...")
                    logger.info(f"📝 更新后source keys: {list(source.keys())}")
                    logger.info(f"🎯 更新后的source包含: credibility={source.get('credibility')}, related_assessment={source.get('related_assessment')}")
                else:
                    logger.warning(f"❌ 未找到评分数据: {source_url}")
                    logger.info(f"📋 source标题: {source.get('title', 'Unknown')}")
                    
            else:
                logger.warning(f"⚠️ source没有URL字段: {source.get('title', 'Unknown')}")
                logger.info(f"📋 source所有字段: {list(source.keys())}")
                    
        logger.info(f"评分信息获取完成: {updated_sources}/{len(unique_sources)} 个数据源已更新")
                    
    except Exception as e:
        logger.error(f"💥 [评分获取] 异常类型: {type(e).__name__}")
        logger.error(f"💥 [评分获取] 异常详情: {str(e)}")
        try:
            import traceback
            logger.error(f"💥 [评分获取] 异常堆栈: {traceback.format_exc()}")
        except:
            pass
        logger.warning(f"获取评分信息失败，将使用默认值")
    
    # 保存数据源到指定目录
    source_files = save_source_data(unique_sources, output_dir=custom_source_dir)
    
    # 创建研究摘要
    summary_path = None
    if report_path and source_files:
        summary_path = create_summary_file(report_path, source_files, query, output_dir=custom_output_dir)

    # 总结文件保存结果
    saved_count = 0
    if report_path:
        saved_count += 1
    if source_files:
        saved_count += len(source_files)
    if summary_path:
        saved_count += 1
    
    if saved_count > 0:
        logger.success(f"研究文件保存完成: 共 {saved_count} 个文件")

    # 数据库持久化逻辑
    db_saved_count = 0
    db_operation_stats = {}
    try:
        from .tools.database import DatabaseManager, batch_map_sources_to_research_records
        
        logger.info("开始数据库持久化操作")
        db_manager = DatabaseManager()
        
        # 测试数据库连接状态
        if not db_manager.test_connection():
            logger.error("数据库连接测试失败，跳过数据库持久化")
        else:
            # 创建数据表
            if db_manager.create_tables():
                logger.info("数据库表创建成功")
                
                # 转换源数据为数据库记录格式
                artifact_id = state.get("artifact_id", 1)  # 从state获取artifact_id，默认为1
                company_id = state.get("company_id", 3)     # 从state获取company_id，默认为3
                created_by = state.get("user_id", 3)        # 从state获取user_id作为created_by，默认为3
                
                db_records = batch_map_sources_to_research_records(unique_sources, company_id, artifact_id, created_by)
                logger.info(f"成功映射 {len(db_records)} 条有效记录")
                
                if db_records:
                    # 执行批量插入操作
                    db_saved_count = db_manager.insert_research_results_batch(db_records)
                    logger.success(f"数据库保存完成: {db_saved_count} 条记录")
                    
                    # 记录操作统计信息
                    db_operation_stats = db_manager.get_operation_stats()
                    db_manager.log_operation_summary()
                    
                    # 🆕 NEW: 立即进行字段评估
                    try:
                        logger.info("开始对新保存的记录进行字段评估...")
                        
                        # 导入评估模块
                        import sys
                        
                        # 添加database_format模块路径
                        database_format_path = os.path.join(os.path.dirname(__file__), '..', 'database_format')
                        if database_format_path not in sys.path:
                            sys.path.insert(0, database_format_path)
                        
                        # 修复导入路径
                        try:
                            from database_updater import DatabaseUpdater
                        except ImportError:
                            # 备用导入方式
                            import importlib.util
                            spec = importlib.util.spec_from_file_location("database_updater",
                                os.path.join(database_format_path, "database_updater.py"))
                            database_updater_module = importlib.util.module_from_spec(spec)
                            spec.loader.exec_module(database_updater_module)
                            DatabaseUpdater = database_updater_module.DatabaseUpdater
                        
                        # 获取研究主题用于评估
                        research_topic = get_research_topic(state["messages"])
                        
                        # 确保数据库路径正确
                        db_path = db_manager.db_path  # 使用当前数据库路径
                        
                        # 创建评估器并设置数据库路径
                        evaluator = DatabaseUpdater()
                        evaluator.db_path = db_path
                        evaluator.config.DATABASE_CONFIG['db_path'] = db_path
                        
                        # 更新研究主题到配置
                        if evaluator.config.research_topic:
                            evaluator.config.research_topic['title'] = research_topic
                            evaluator.config.research_topic['description'] = f"研究主题：{research_topic}"
                        
                        logger.info(f"开始评估数据库: {db_path}")
                        logger.info(f"研究主题: {research_topic}")
                        
                        # 获取需要评估的记录（限制数量避免过长处理时间）
                        references_to_evaluate = evaluator.get_references_to_update(limit=50)
                        
                        if references_to_evaluate:
                            logger.info(f"发现 {len(references_to_evaluate)} 条需要评估的记录")
                            
                            # 执行批量评估
                            evaluation_result = evaluator.process_batch(references_to_evaluate)
                            
                            if evaluation_result.successful > 0:
                                logger.success(f"字段评估完成: {evaluation_result.successful} 条记录已完善")
                                logger.info(f"评估成功率: {evaluation_result.successful}/{evaluation_result.total_processed}")
                            else:
                                logger.warning("字段评估未处理任何记录")
                                
                            # 显示评估后的统计信息
                            final_stats = evaluator.get_statistics()
                            if final_stats:
                                logger.info("评估后统计:")
                                logger.info(f"  - 总记录数: {final_stats.get('total_references', 0)}")
                                logger.info(f"  - 未分类记录: {final_stats.get('unclassified', 0)}")
                                
                        else:
                            logger.info("没有需要评估的新记录")
                            
                    except ImportError as import_error:
                        logger.warning(f"无法导入评估模块: {import_error}")
                        logger.info("评估将在后续步骤中进行")
                    except Exception as eval_error:
                        logger.error(f"字段评估过程出错: {eval_error}")
                        logger.info("数据已保存，将在后续步骤中重试评估")
                        # 不抛出异常，允许主流程继续
                    
                else:
                    logger.warning("没有有效的数据记录可保存到数据库")
            else:
                logger.error("数据库表创建失败，跳过数据库持久化")
            
    except ImportError as e:
        logger.error(f"数据库模块导入失败: {str(e)}")
    except Exception as e:
        logger.error(f"数据库保存失败: {str(e)}")
        # 数据库操作失败不影响主流程，继续返回结果

    return {
        "messages": [AIMessage(content=result.content)],
        "sources_gathered": unique_sources,
        "saved_report_path": report_path,
        "saved_source_files": source_files,
        "saved_summary_path": summary_path,
        "db_saved_count": db_saved_count
    }


# Create our Agent Graph
builder = StateGraph(OverallState, config_schema=Configuration)

# Define the nodes we will cycle between
builder.add_node("generate_query", generate_query)
builder.add_node("web_research", web_research)
builder.add_node("reflection", reflection)
builder.add_node("finalize_answer", finalize_answer)

# Set the entrypoint as `generate_query`
# This means that this node is the first one called
builder.add_edge(START, "generate_query")
# Add conditional edge to continue with search queries in a parallel branch
builder.add_conditional_edges(
    "generate_query", continue_to_web_research, ["web_research"]
)
# Reflect on the web research
builder.add_edge("web_research", "reflection")
# Evaluate the research
builder.add_conditional_edges(
    "reflection", evaluate_research, ["web_research", "finalize_answer"]
)
# Finalize the answer
builder.add_edge("finalize_answer", END)

graph = builder.compile(name="pro-search-agent")
