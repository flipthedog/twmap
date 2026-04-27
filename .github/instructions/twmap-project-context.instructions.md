---
description: "Use when working on TWMap features, data loading, image generation, S3 snapshot processing, or ffmpeg timelapse scripts. Defines project context and coding rules for this repository."
name: "TWMap Project Context"
applyTo: "**"
---
# TWMap Project Context

This repository builds Tribal Wars world maps from time-based snapshots and turns them into timelapse videos.

## Project Purpose

- Generate map images for Tribal Wars worlds from snapshot data.
- Each map represents one world snapshot at one point in time.
- Process snapshots collected over weeks or months to produce chronological image series.
- Create timelapse videos from those image series using ffmpeg shell scripts.

## Data and Pipeline

- Primary source data is stored in S3 and loaded through project data loader components.
- Typical flow: load snapshot files -> filter/aggregate data -> render map image -> save image output -> build timelapse video.
- Preserve chronological order and timestamp consistency when processing snapshots.
- Do not change raw input data formats unless explicitly requested.

## Coding Guidelines For Agents

- Prefer extending existing modules under twmap/ instead of creating parallel one-off scripts.
- Keep server and world handling explicit and consistent (for example en146 style naming).
- Preserve output determinism: same input snapshot should produce the same rendered output.
- For Python changes, favor clear DataFrame transformations and avoid unnecessary full-data copies in hot paths.
- For rendering changes, keep visuals readable at timelapse scale and avoid regressions in legends, labels, and aspect-ratio handling.
- For shell/ffmpeg changes, keep scripts non-interactive and reproducible.
- Follow existing tooling workflow with uv for dependency and run commands.

## What Good Changes Look Like

- New functionality supports snapshot-based map generation and/or timelapse production.
- Changes improve rendering quality, processing reliability, or automation of the existing pipeline.
- Output paths and naming stay consistent with current repository conventions.
