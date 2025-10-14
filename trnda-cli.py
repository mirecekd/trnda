#!/usr/bin/env python3
"""
TRNDA CLI - Command Line Interface  
Simple wrapper that passes S3 paths to the agent
"""

import os
import sys
import argparse

# Import directly from trnda-agent.py
import importlib.util
spec = importlib.util.spec_from_file_location("trnda_agent", 
                                               os.path.join(os.path.dirname(__file__), "trnda-agent.py"))
trnda_agent_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(trnda_agent_module)

# Get the process function
process_image_standalone = trnda_agent_module.process_image_standalone


def main():
    """Main CLI entry point"""
    # Note: AWS credentials are handled automatically:
    # - On EC2: Uses IAM instance profile role
    # - Locally: Uses AWS_PROFILE environment variable or default profile
    
    parser = argparse.ArgumentParser(
        description='TRNDA - Trask Ručně Nakreslí, Dokončí AWS',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process from S3 (automatic download/upload)
  python trnda-cli.py s3://tr-sw-trnda-diagrams/input/sample1.jpg
  
  # Short S3 path (bucket is auto-added)
  python trnda-cli.py sample1.jpg
  
  # With client name
  python trnda-cli.py sample1.jpg --client "ACME Corp"
  
  # Local file (traditional mode)
  python trnda-cli.py local/diagram.jpg
  
  # Multiple images
  python trnda-cli.py sample1.jpg sample2.jpg

Note: 
- S3 paths starting with 's3://' are processed from S3
- Short names like 'sample1.jpg' are treated as s3://tr-sw-trnda-diagrams/input/sample1.jpg
- Local file paths work as before
        """
    )
    
    parser.add_argument(
        'images',
        nargs='+',
        help='Image path(s): S3 URI (s3://bucket/key), short name (sample1.jpg), or local path'
    )
    
    parser.add_argument(
        '-c', '--client',
        help='Client or project name (optional)',
        default=None
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("TRNDA - Trask Ručně Nakreslí, Dokončí AWS")
    print("=" * 70)
    print(f"Processing {len(args.images)} image(s)")
    if args.client:
        print(f"Client: {args.client}")
    print("=" * 70)
    print()
    
    results = []
    
    for idx, image_path in enumerate(args.images, 1):
        print(f"[{idx}/{len(args.images)}] Processing: {image_path}")
        print("-" * 70)
        
        try:
            # Process image - agent handles S3 automatically
            output_location = process_image_standalone(
                image_path=image_path,
                client_name=args.client
            )
            
            results.append({
                'image': image_path,
                'output': output_location,
                'success': True
            })
            
            print()
            print(f"[OK] Completed")
            print()
            
        except Exception as e:
            print()
            print(f"[ERROR] Failed to process {image_path}")
            print(f"        {e}")
            print()
            
            import traceback
            if args.verbose:
                traceback.print_exc()
            
            results.append({
                'image': image_path,
                'output': None,
                'success': False,
                'error': str(e)
            })
            
            if len(args.images) > 1:
                # Continue with next image
                print("Continuing with next image...")
                print()
                continue
            else:
                # Single image - exit with error
                sys.exit(1)
    
    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful
    
    print(f"Total: {len(results)} | Success: {successful} | Failed: {failed}")
    print()
    
    if successful > 0:
        print("Successful outputs:")
        for r in results:
            if r['success']:
                print(f"  - {r['image']}")
                print(f"    → {r['output']}")
        print()
    
    if failed > 0:
        print("Failed:")
        for r in results:
            if not r['success']:
                print(f"  - {r['image']}")
                print(f"    Error: {r.get('error', 'Unknown error')}")
        print()
        sys.exit(1)
    
    print("=" * 70)
    print("All done!")
    print("=" * 70)


if __name__ == "__main__":
    main()
