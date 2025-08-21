"""Main entry point for database format evaluation system."""

import argparse
import sys
import os
from pathlib import Path
from loguru import logger
from dotenv import load_dotenv

from .database_updater import DatabaseUpdater
from .config import config

def setup_logging(verbose: bool = False):
    """Set up logging configuration."""
    logger.remove()  # Remove default handler
    
    if verbose:
        logger.add(sys.stdout, level="DEBUG", 
                  format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    else:
        logger.add(sys.stdout, level="INFO",
                  format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>")

def main():
    """Main function for database evaluation."""
    parser = argparse.ArgumentParser(description="Database Reference Evaluation System")
    parser.add_argument('--batch-size', type=int, default=10,
                       help='Number of references to process in each batch (default: 10)')
    parser.add_argument('--limit', type=int, default=None,
                       help='Maximum number of references to process (default: all)')
    parser.add_argument('--stats', action='store_true',
                       help='Show database statistics only')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Enable verbose logging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show references that would be processed without updating')
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.verbose)
    
    # Load environment variables from .env file in backend directory
    backend_root = Path(__file__).parent.parent.parent
    env_path = backend_root / '.env'
    if env_path.exists():
        load_dotenv(env_path)
        logger.debug(f"Loaded environment variables from {env_path}")
    
    # Get API key from environment
    api_key = os.getenv('ANTHROPIC_API_KEY')
    if not api_key:
        logger.error("ANTHROPIC_API_KEY not found in environment variables or .env file")
        logger.error("Please set the environment variable or add it to .env file")
        return 1
    
    # Update config with API key
    config.LLM_CONFIG['api_key'] = api_key
    
    # Initialize updater
    try:
        updater = DatabaseUpdater()
        
        # Update batch size if specified
        if args.batch_size:
            updater.batch_size = args.batch_size
            
    except Exception as e:
        logger.error(f"Failed to initialize database updater: {str(e)}")
        return 1
    
    # Show statistics
    if args.stats:
        logger.info("Database Statistics:")
        stats = updater.get_statistics()
        
        if stats:
            logger.info(f"Total references: {stats['total_references']}")
            logger.info(f"Unclassified: {stats['unclassified']}")
            logger.info("Credibility distribution:")
            logger.info(f"  - Low: {stats['credibility']['low']}")
            logger.info(f"  - Medium: {stats['credibility']['medium']}")
            logger.info(f"  - High: {stats['credibility']['high']}")
            logger.info("Relevance distribution:")
            logger.info(f"  - Low (0.0-0.3): {stats['relevance']['low']}")
            logger.info(f"  - Medium (0.3-0.6): {stats['relevance']['medium']}")
            logger.info(f"  - High (0.6-0.8): {stats['relevance']['high']}")
            logger.info(f"  - Very High (0.8-1.0): {stats['relevance']['very_high']}")
        return 0
    
    # Dry run - show what would be processed
    if args.dry_run:
        references = updater.get_references_to_update(limit=args.limit)
        logger.info(f"Would process {len(references)} references:")
        
        for i, ref in enumerate(references[:10]):  # Show first 10
            logger.info(f"{i+1}. ID: {ref.id} - {ref.reference_title[:60]}...")
            logger.info(f"   URL: {ref.reference_url}")
            logger.info(f"   Current type: {ref.reference_type}, Credibility: {ref.credibility}, Relevance: {ref.related_assessment}")
            
        if len(references) > 10:
            logger.info(f"... and {len(references) - 10} more references")
            
        return 0
    
    # Process references
    logger.info("Starting reference evaluation process...")
    logger.info(f"Research topic: {config.research_topic['title']}")
    logger.info(f"Batch size: {updater.batch_size}")
    
    try:
        if args.limit:
            # Process limited number
            references = updater.get_references_to_update(limit=args.limit)
            if references:
                result = updater.process_batch(references)
                logger.info(f"\nProcessing complete!")
                logger.info(result.summary())
            else:
                logger.info("No references found that need evaluation")
        else:
            # Process all
            results = updater.process_all()
            logger.info(f"\nAll processing complete!")
            logger.info(f"Total processed: {results['total_processed']}")
            logger.info(f"Successful: {results['successful']}")
            logger.info(f"Failed: {results['failed']}")
            logger.info(f"Success rate: {results['success_rate']:.1f}%")
            
    except KeyboardInterrupt:
        logger.warning("Process interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Error during processing: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())