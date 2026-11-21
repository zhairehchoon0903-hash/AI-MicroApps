# Character Continuity Studio

The Character Continuity Studio extends the existing character records without changing or discarding the original character fields. It adds a visual bible under each character's `visual_bible` object.

## What is tracked

- **Permanent identity anchors:** face structure, eyes, hair identity, distinctive marks, body/silhouette, identity palette, must-keep traits, and traits the design must never drift into.
- **Life-stage variants:** Baby/Infant, Child, Teenager, Adult, and Older Adult. Each stage has its own appearance/performance notes, costume/props, development notes, and optional reference image.
- **Negative prompt:** reusable exclusions to help prevent visual drift.
- **Prompt builder:** combines the approved identity anchors with the selected age-stage profile and existing character notes.

## Storage and privacy

Reference images are resized in the browser to a maximum 384-pixel dimension and JPEG-compressed before saving. Each stored image is limited to 160 KB of data-URL text. Images are stored inside that character's project record; no image is sent to a third-party image-generation provider by this feature. For server-backed projects, the existing Film Studio project-save endpoint persists the character record. The existing 2 MB project payload limit still applies.

## Workflow

1. Create a character in the existing Character Bible.
2. Open Character Continuity and choose the film and character.
3. Enter permanent identity anchors only when those details are established. Leave unknown traits blank.
4. Select each life stage and enter the age-appropriate design, costume, and development notes. Upload an optional reference image for that stage.
5. Save the profile. Switching stages or characters also saves the current edits.
6. Copy the generated prompt into the image/video workflow when ready. This feature itself does not generate images or video, spend credits, or call a paid provider.

## Data compatibility

Existing character fields (`id`, `name`, `role`, `visual`, `personality`, `continuity`) remain unchanged. New data is stored as `character.visual_bible.identity_anchors`, `character.visual_bible.age_variants`, and `character.visual_bible.negative_prompt`. Older characters are initialized lazily when opened; their existing content is preserved.
