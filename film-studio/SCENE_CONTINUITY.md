# Scene Continuity Studio

The Scene Continuity Studio adds a project-scoped location visual bible and a shot-by-shot continuity ledger to Film Studio. It is designed to preserve approved visual facts without inventing unconfirmed worldbuilding.

## Location visual bible

Each location record is stored in `project.scene_visual_bible.locations` and includes: name, type/status, geography, architecture/materials, landmarks/spatial layout, palette/textures, atmosphere/climate/sound, default lighting, and details that must not drift. A location can remain a blank or partially completed template until story canon establishes its details.

The generated location prompt repeats only the saved values. Missing values are explicitly marked as not established and should not be invented. Use it as an environment continuity block for establishing frames, reverse angles, interiors/exteriors, and later image-to-video prompts.

## Shot continuity ledger

Entries are stored in `project.scene_visual_bible.ledger`. Each entry can record scene and shot references, location, story day/time, weather/season/light, character blocking and screen direction, costume/props/hand placement, injuries/damage/physical condition, weapons and powers state, entrances/exits/action progression, matches to adjacent shots, and open questions. Entries can be removed individually.

## Persistence and integration

The browser workspace reads and writes the existing `openmontage-film-studio-v1` project store. Updates emit `film-studio-scene-continuity-updated`; the main app persists the project and includes `scene_visual_bible` in the existing studio backend sync payload. Existing scene, shot, character, screenplay, and character visual-bible data are not replaced.

## Workflow

1. Select a film project.
2. Create a location record for each recurring place; fill only approved facts.
3. Save and copy the location-safe prompt when preparing visual shots.
4. Add a ledger entry for each important shot or continuity checkpoint.
5. Compare adjacent entries before generating or editing a sequence.

## Scope and safety

This is a planning and recordkeeping feature. It does not generate images or video, call external AI providers, upload reference images, spend credits, or create canon. The Five Kingdoms and other world details remain intentionally unspecified until approved by the director.
