# Third-party notices

This repository depends on third-party packages installed from the hash-locked requirements files. Those packages and any components shipped inside their wheels retain their own licenses, copyright notices and attribution requirements.

No license for a dependency is replaced by this repository's MIT license. A dependency summary is not a complete notice bundle for a packaged application.

## Direct dependencies

The following identifies upstream license information for pinned direct runtime dependencies. Check the license files shipped in the installed distributions for the complete terms, bundled components and exceptions.

| Package | Upstream terms and source |
| --- | --- |
| NumPy | BSD-3-Clause and additional bundled-component licenses; [license information](https://numpy.org/doc/stable/license.html) |
| SciPy | BSD-3-Clause and bundled-component notices; [license files](https://github.com/scipy/scipy/blob/main/LICENSE.txt) |
| TensorFlow | Apache-2.0 and third-party notices; [license](https://github.com/tensorflow/tensorflow/blob/master/LICENSE) |
| Keras | Apache-2.0; [license](https://github.com/keras-team/keras/blob/master/LICENSE) |
| Matplotlib | Matplotlib's PSF-based license and bundled notices; [license information](https://matplotlib.org/stable/project/license.html) |
| PyQt5 | GPLv3 or a Riverbank commercial license; [licensing](https://www.riverbankcomputing.com/software/pyqt/intro) |
| scikit-fuzzy | BSD-3-Clause; [license](https://github.com/scikit-fuzzy/scikit-fuzzy/blob/master/LICENSE.txt) |
| NetworkX | BSD-3-Clause; [license](https://networkx.org/documentation/stable/license.html) |
| python-dotenv | BSD-3-Clause; [license](https://github.com/theskumar/python-dotenv/blob/main/LICENSE) |
| jsonschema | MIT; [license](https://github.com/python-jsonschema/jsonschema/blob/main/COPYING) |
| RPi.GPIO | MIT; [package record](https://pypi.org/project/RPi.GPIO/0.7.1/) |

Direct development tools are pytest, pytest-cov and Ruff under MIT, and pip-audit under Apache-2.0. Their transitive dependencies have separate terms.

## PyQt and Qt

The pinned PyPI PyQt5 distribution identifies its license as GPL v3. Riverbank also offers commercial licensing. Qt libraries may be supplied by the operating system on ARM or by a separate wheel on desktop platforms, and have their own applicable terms. Packaging must account for the actual PyQt and Qt distributions being shipped, rather than assuming the project's MIT license covers them.

## Redistribution inventory

Before distributing wheels, installers, containers or executable bundles, inventory the distributions and native libraries actually included. Retain their license and notice files and satisfy the terms of the versions being shipped. In a development environment, installed metadata can be inspected with:

```bash
.venv/bin/python -m pip inspect > dependency-inventory.json
```

The output is an inventory aid, not a legal compatibility decision or a substitute for upstream license texts. Refresh these notices when dependencies or packaging change.
