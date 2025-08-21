#!/usr/bin/env python3
"""
Demonstration of the Citation Agent configuration system.
Shows how to load, validate, and use configuration in different ways.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from citation_agent.configuration import Configuration, CitationStyle, OutputFormat


def demo_basic_usage():
    """Demonstrate basic configuration usage."""
    print("=== Basic Configuration Usage ===")
    
    # Create default configuration
    config = Configuration()
    print(f"Default citation style: {config.citation_style.value}")
    print(f"Default output formats: {[fmt.value for fmt in config.output_formats]}")
    print(f"Default report length limit: {config.max_report_length}")
    print()


def demo_environment_loading():
    """Demonstrate loading configuration from environment variables."""
    print("=== Environment Variable Loading ===")
    
    # Set some environment variables
    os.environ["CITATION_STYLE"] = "MLA"
    os.environ["MAX_REPORT_LENGTH"] = "3000"
    os.environ["OUTPUT_FORMATS"] = "markdown,pdf"
    
    # Load configuration from environment
    config = Configuration.from_runnable_config()
    print(f"Citation style from env: {config.citation_style.value}")
    print(f"Max report length from env: {config.max_report_length}")
    print(f"Output formats from env: {[fmt.value for fmt in config.output_formats]}")
    print()
    
    # Clean up
    del os.environ["CITATION_STYLE"]
    del os.environ["MAX_REPORT_LENGTH"]
    del os.environ["OUTPUT_FORMATS"]


def demo_validation():
    """Demonstrate configuration validation."""
    print("=== Configuration Validation ===")
    
    # Create configuration with some potentially problematic values
    config = Configuration(
        min_source_credibility=0.05,  # Very low
        max_report_length=500,        # Very short
        content_similarity_threshold=0.98,  # Very high
    )
    
    warnings = config.validate_configuration()
    if warnings:
        print("Configuration warnings:")
        for warning in warnings:
            print(f"  - {warning}")
    else:
        print("No configuration warnings")
    print()


def demo_model_configs():
    """Demonstrate model-specific configuration generation."""
    print("=== Model-Specific Configurations ===")
    
    config = Configuration(
        content_analysis_model="gpt-4o-mini",
        report_generation_model="gpt-4o",
        temperature=0.3,
        llm_timeout=60
    )
    
    # Get configurations for different model types
    content_config = config.get_model_config("content_analysis")
    report_config = config.get_model_config("report_generation")
    
    print("Content analysis model config:")
    for key, value in content_config.items():
        print(f"  {key}: {value}")
    
    print("\nReport generation model config:")
    for key, value in report_config.items():
        print(f"  {key}: {value}")
    print()


def demo_runtime_info():
    """Demonstrate runtime information generation."""
    print("=== Runtime Information ===")
    
    config = Configuration()
    runtime_info = config.get_runtime_info()
    
    print("Current configuration summary:")
    print(f"  Models: {runtime_info['models']}")
    print(f"  Citation style: {runtime_info['citation_style']}")
    print(f"  Output formats: {runtime_info['output_formats']}")
    print(f"  Quality check enabled: {runtime_info['quality_check_enabled']}")
    print(f"  Processing limits: {runtime_info['limits']}")
    print()


def demo_custom_configuration():
    """Demonstrate creating custom configuration."""
    print("=== Custom Configuration ===")
    
    # Create a custom configuration for academic research
    academic_config = Configuration(
        citation_style=CitationStyle.APA,
        output_formats=[OutputFormat.PDF, OutputFormat.HTML],
        max_report_length=8000,
        include_methodology_section=True,
        quality_check_enabled=True,
        min_quality_score=0.8,
        temperature=0.2  # Lower temperature for more consistent output
    )
    
    print("Academic research configuration:")
    print(f"  Citation style: {academic_config.citation_style.value}")
    print(f"  Output formats: {[fmt.value for fmt in academic_config.output_formats]}")
    print(f"  Max report length: {academic_config.max_report_length}")
    print(f"  Include methodology: {academic_config.include_methodology_section}")
    print(f"  Min quality score: {academic_config.min_quality_score}")
    print()


def main():
    """Run all configuration demonstrations."""
    print("Citation Agent Configuration System Demo")
    print("=" * 50)
    
    demo_basic_usage()
    demo_environment_loading()
    demo_validation()
    demo_model_configs()
    demo_runtime_info()
    demo_custom_configuration()
    
    print("=" * 50)
    print("Demo completed! Check the configuration.py file for more details.")


if __name__ == "__main__":
    main()