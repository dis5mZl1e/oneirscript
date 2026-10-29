# Contributing to Oneirscript

Thank you for helping improve Oneirscript. Contributions can include gameplay
ideas, bug reports, playtest feedback, translations, documentation, assets and
code.

This English document is the primary contribution guide.
[简体中文参考译文](CONTRIBUTING_CN.md).

## Project direction

The author particularly welcomes contributions that:

- Introduce inventive gameplay and meaningful interactions between systems.
- Explore crossovers with other works or creative fields when the necessary
  permissions and compatible licenses are in place.
- Make rules, costs, conditions and consequences easier for players to
  understand through clear information and feedback.
- Reduce repetitive busywork while preserving meaningful decisions and the
  game's tactical character.

Explain the player experience you want to improve, as well as the implementation.
For a substantial feature or redesign, opening an issue first can help identify
differences in direction before you invest in a large implementation. Discussion
does not guarantee that a later submission will be merged.

## What you may submit

You may submit code or assets that you are entitled to contribute under the
project's applicable licenses. The material does not have to be written entirely
by you: properly authorized third-party work, adaptations and tool-assisted work
are welcome.

For material from other sources, identify its origin, license, attribution
requirements and relevant modifications. For a crossover, explain the permission
or license covering the names, characters, artwork, audio or other material used.
Do not assume that publicly accessible material is licensed for reuse.

Project-owned code is licensed under [GPL-3.0-only](LICENSE); assets and external
components can have different terms. Consult [LICENSING.md](LICENSING.md) and
[THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). This guide does not grant rights
to someone else's work or replace any applicable license.

## Contributor review and tool assistance

**The submitter must review the code before submitting it**, regardless of who
wrote it or which tools helped produce it. Review includes understanding the
behavior, checking the affected paths, identifying important risks and verifying
that the contribution is appropriate to submit.

AI and other tools may assist with implementation, analysis, documentation and
testing. Tool-generated review alone does not replace the submitter's substantive
human review. You should be able to explain how the change works and its known
limitations.

Be transparent about material third-party sources and significant tool or AI
assistance. Describe the areas involved; you do not need to publish private
prompts, complete conversation histories, credentials or personal information.
The existing [AI and contribution policy](README_EN.md#en-ai-policy) provides
additional detail.

## Preparing a change

1. Fork the repository and create a branch for your change.
2. Keep the change focused. Separate unrelated fixes or features when practical.
3. Preserve relevant copyright, attribution and license notices.
4. Review the implementation and check the behavior it changes.
5. Update documentation and relevant language entries when behavior or UI text
   changes.
6. Open a pull request with the information below.

For setup, see [Running from source](README_EN.md#en-source). The
[technical guide](TECHNICAL_EN.md) covers the architecture, code locations and
available development checks.

### Validation

Run checks relevant to the change and inspect affected gameplay or UI behavior.
Available smoke commands include:

```sh
python run_demo.py --smoke --save-dir save-smoke
python run_demo.py --smoke --image-smoke --save-dir save-image-smoke
python run_demo.py --smoke --fx-smoke --save-dir save-fx-smoke
```

Use disposable save directories and back up personal saves. These smoke checks
do not replace focused gameplay testing or native platform checks. The full
maintainer test suite and release build tools are not included in this
source-focused repository.

Report only the checks you actually ran. If a platform, interaction or migration
remains untested, say so.

## Pull request checklist

Include the following in your description:

- **Purpose:** the problem or player experience addressed, with a concrete
  before/after example where useful.
- **Approach and scope:** how the change works and which systems it affects.
- **Provenance and permissions:** sources, licenses, attribution and any crossover
  permissions relevant to the submitted material.
- **Review and assistance:** confirmation of your own review and significant tool
  or AI assistance used.
- **Validation:** commands or playtest steps performed, environment and results.
- **Compatibility and limitations:** effects on saves, controls, language support,
  platforms, dependencies or existing behavior, including unverified areas.
- **Presentation:** screenshots or a short recording for visible changes when
  they help explain the result.

Do not include credentials, private third-party code, personal information or
other material you are not authorized to share.

## How merge decisions are made

The author reviews proposed changes for compatibility with the existing game,
fit with its themes and gameplay direction, and the practical consequences of
maintaining the implementation. Licensing, clarity, testing and regressions also
inform that review.

A submission may need revision, be split into smaller changes, be deferred or be
declined. Passing tests and following this guide do not guarantee a merge, and
there is no guaranteed review or merge schedule.

## Independent forks and different directions

If a branch substantially differs in difficulty, theme, gameplay or
implementation approach, the author recommends maintaining it as an independent
fork or repository. This gives its maintainers room to pursue that direction
without requiring agreement with the main game's design.

Clearly identify the fork's maintainer and its relationship to Oneirscript, and
direct its support requests to that maintainer. An independent version is not an
official release merely because it is derived from this project or submitted as
a pull request.

This recommendation does not add restrictions to the rights granted by the GPL
or the applicable asset licenses. See the [fork policy](README_EN.md#en-ai-policy)
for the existing responsibility and licensing boundaries.

## Reporting problems

For a bug report, include the commit or version, operating system, Python
version, terminal, reproduction steps and expected versus actual behavior.
Remove sensitive information from logs and saves before sharing them. Do not
disclose security-sensitive details in a public issue.

Keep discussion constructive and focused on the behavior or proposal. Explain
disagreements with concrete examples so that different design goals can be
understood.
