# Data Models

API response and request models.

## Overview

All data models are defined in `scambus_client/models.py`.

## Core Models

- `JournalEntry` - Journal entry data
- `Identifier` - Identifier data (phone, email, etc.)
- `Case` - Investigation case data
- `ExportStream` - Export stream data
- `Media` - Media file data
- `Tag` - Tag data

## Detail Models

- `DetectionDetails` - Detection-specific details
- `PhoneCallDetails` - Phone call-specific details
- `EmailDetails` - Email-specific details

For complete model definitions, see the source code in `scambus_client/models.py`.
