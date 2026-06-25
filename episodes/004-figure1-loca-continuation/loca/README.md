# Episode-local LOCA assets

This directory is reserved for Figure 1 LOCA/Trilinos source, CMake/build files, run configurations, and raw solver artifacts that are specific to Episode 4.

Initial implementation constraints:

- start with a serial dense LOCA/LAPACK configuration;
- use Sacado automatic differentiation for the state Jacobian;
- keep Python as the semantic model reference;
- write normalized outputs using the backend-neutral schema described in `../docs/planning-decisions.md`;
- do not promote C++/Trilinos infrastructure outside this episode unless it becomes documented shared backend infrastructure.
