---
hide:
  - navigation
title: Home
---

# Home
This documentation website composes the final hand-in for the course Software Development for Technical Applications (VSMN20) at Lund University. This page contains a brief theoretical introduction to groundwater flow, details on the program structure, manuals for both the application and the module. Each part has its own page, which can be reached by using the top navigation tab. A git repository containing the latest program version is available [here](https://youtu.be/dQw4w9WgXcQ).

### Acknowledgements
The website is built using [MkDocs](https://www.mkdocs.org/) with a theme and additional functionality from [Material for MkDocs](https://squidfunk.github.io/mkdocs-material/). For the source code documentation, the plugin [mkdocstrings](https://mkdocstrings.github.io/) was used. The application UI was inspired by multiple QtDesigner tutorials made by [Wanderson](https://www.youtube.com/c/WandersonIsMe) on YouTube.

??? info "Python packages"
    This program was written in a default Anaconda3 environment, with the addition a few of packages. I recommend that the conda environment is updated, since I myself experienced some problems. Further that that pip is used to verify the installment of the neccecary packages that are not included in Anaconda3:
    ``` { .annotate }
    conda update --all 
    pip install gmsh calfem-python 
    ```
    <br>If one want to experiment with MkDocs do so by installing the packages and host the website locally with:
    ``` { .annotate }
    pip install mkdocs mkdocs-material mkdocstrings
    ...\MkDocs> mkdocs serve
    ```
    