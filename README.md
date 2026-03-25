# pokediamondDA

[![build](https://github.com/pret/pokediamond/actions/workflows/build.yml/badge.svg?branch=master)](https://github.com/pret/pokediamond/actions/workflows/build.yml)

`pokediamondDA` is a personal localization-focused fork of the `pret/pokediamond` decompilation project.

## Project meaning and goal

The goal of this repository is to produce a fully playable Danish version of Pokemon Diamond by translating the in-game text and UI while keeping the original ROM behavior and build pipeline.

This includes:

- Translating message banks under `files/msgdata/msg/*.gmm`
- Adapting Pokedex and species-related text for Danish presentation
- Preserving control codes and technical message structure used by `msgenc`

## Build outputs

This project builds the same base ROM targets as upstream:

- [**pokediamond.us.nds**](https://datomatic.no-intro.org/index.php?page=show_record&s=28&n=1015) `sha1: a46233d8b79a69ea87aa295a0efad5237d02841e`
- [**pokepearl.us.nds**](https://datomatic.no-intro.org/index.php?page=show_record&s=28&n=1016) `sha1: 99083bf15ec7c6b81b4ba241ee10abd9e80999ac`

## Setup and contribution

- Setup instructions: [INSTALL.md](INSTALL.md)
- Contribution guidelines: [CONTRIBUTING.md](CONTRIBUTING.md)
- Upstream project network: [pret.github.io](https://pret.github.io/)
