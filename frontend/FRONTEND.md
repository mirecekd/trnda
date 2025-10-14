# TRNDA Frontend - Requirements

The frontend will serve the backend by uploading photos and metadata to S3 bucket.

The frontend will be implemented in the `frontend/` folder. No other files outside this folder will be updated except README.md.

## Features

The web page (simple design) should have:

- Ability to load a photo with a diagram from a phone
- The uploaded photo can be rotated correctly (rotation icons - just icons - preferably in the corner of the photo and over it, so it's always visible), so that the bottom is at the bottom and not, for example, standing up
- Below the photo there will be a field for 1900 characters - no more is possible, and diacritics will be removed - only basic ASCII characters can be used, which will be saved as metadata (`aws s3 cp "$IMAGE_FILE" "s3://$BUCKET/input/" --metadata client-info="$CLIENT_INFO"`) with the photo to S3
- The frontend should run on AWS - suggest the best solution (cost vs usability)

## Implementation Notes

- Single page application (HTML/CSS/JavaScript)
- Mobile-first responsive design
- Direct camera capture support
- Image rotation with visual feedback
- ASCII-only metadata (automatic diacritics removal)
- AWS S3 direct upload with Cognito authentication
- Cost-effective deployment (~$0.50-1/month)

## Technical Stack

- **Frontend:** Vanilla JavaScript + AWS SDK v3
- **Hosting:** S3 Static Website Hosting
- **Authentication:** Cognito Identity Pool (unauthenticated)
- **Storage:** Direct upload to `your-trnda-s3-bucket/input/`

## Architecture Decision

Selected architecture: **S3 Static Website + Cognito Identity Pool**

### Advantages:
- Lowest cost (~$0.50-1/month for thousands of uploads)
- Secure - temporary AWS credentials without registration
- Mobile optimized
- No server maintenance
- Auto-scaling

### Components:
1. **S3 Static Website Hosting** - hosting HTML/JS/CSS
2. **Cognito Identity Pool** - anonymous S3 upload access
3. **IAM Role** - permissions only for upload to `input/` folder

## Deployment

See `README.md` for detailed setup and deployment instructions.
