# lattice-size-01 analysis (validation)

## Reach

| size | worlds | living | extinct | stagnant | unreached | ext_unreached | too_many_unreached |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 24 | 4 | 4 | 0 | 0 | 0 | 4 | 0 |
| 32 | 4 | 4 | 0 | 0 | 0 | 4 | 0 |
| 48 | 4 | 4 | 0 | 0 | 0 | 4 | 0 |
| 64 | 4 | 4 | 0 | 0 | 0 | 4 | 0 |

## Primary tests

| endpoint | rho | p | p_holm | rho_A | rho_B | outcome | mean_L24 | mean_L32 | mean_L48 | mean_L64 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| E1_t64 | 0.338062 | 0.371814 | 0.371814 | nan | 0.516398 | inconclusive | 0.75 | 0.75 | 1 | 1 |
| E1_t256 | 0.663325 | 0.0169915 | 0.033983 | 0.507093 | 0.894427 | differs | 0.25 | 0.5 | 1 | 1 |
| E2_t64 | 0.880277 | 0.00049975 | 0.00249875 | 0.932673 | 0.83957 | differs | 0.132653 | 0.352041 | 0.857143 | 0.994898 |
| E2_t256 | 0.815499 | 0.00049975 | 0.00249875 | 0.642024 | 0.8318 | differs | 0.0918367 | 0.112245 | 0.540816 | 0.928571 |
| E3 | 0.867864 | 0.0009995 | 0.0029985 | 0.8318 | 0.883788 | differs | 0.484694 | 0.586735 | 1 | 1 |

## Attribution

| part | value | lo90 | hi90 | entirely_on_delta_side |
| --- | --- | --- | --- | --- |
| S_t1 | 0.642857 | 0.44898 | 0.826531 | 1 |
| S_t2 | 0.816327 | 0.658163 | 0.954082 | 1 |
| F_small | -0.239796 | -0.423469 | -0.0765306 | 0 |
| F_large | -0.0663265 | -0.19898 | 0 | 0 |

| delta | check_S_t2_plus_F_small | check_S_t1_plus_F_large | outcome |
| --- | --- | --- | --- |
| 0.576531 | 0.576531 | 0.576531 | size, not filter length |

## Neutral scaling

| endpoint | rho | p_uncorrected | label |
| --- | --- | --- | --- |
| E1_tN | 0.338062 | 0.371814 | consistent with the filter's neutral scaling |
| E2_tN | 0.783054 | 0.00049975 | beyond the filter's neutral scaling |

## Patterns (descriptive)

| pattern | statistic | value | holds |
| --- | --- | --- | --- |
| supply-like (A1a) | origins slope; rho(L, ff_longest) | 1.273 [0.9881, 1.875]; 0.8549 [0.7785, 0.9374] | 0 |
| smooth (A1b) | rho(L, ff_longest) interval; rise in mean E2 and largest step share | [0.7785, 0.9374]; t64 rise 0.8622, largest step 0.5858; t256 rise 0.8367, largest step 0.5122 | 0 |
| pattern-like (A2) | rho(L, xi); median xi at largest L; one-cluster share at smallest L | 0.7044 [0.5171, 0.8698]; 3; 9/18 | 0 |

## Size x filter

| size | t | diagonal | worlds | established | mean_E2 | median_E2 | episodes | losses | losses16 | median_longest | present_at_end |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 24 | 36 | 1 | 4 | 3 | 0.173469 | 0.0714286 | 5 | 4 | 3 | 48 | 1 |
| 24 | 64 | 0 | 4 | 3 | 0.132653 | 0.0408163 | 4 | 3 | 2 | 32 | 1 |
| 24 | 144 | 0 | 4 | 1 | 0.0918367 | 0 | 1 | 0 | 0 | 0 | 0 |
| 24 | 256 | 0 | 4 | 1 | 0.0918367 | 0 | 1 | 0 | 0 | 0 | 0 |
| 32 | 36 | 0 | 4 | 4 | 0.403061 | 0.397959 | 4 | 3 | 3 | 336 | 1 |
| 32 | 64 | 1 | 4 | 3 | 0.352041 | 0.346939 | 5 | 4 | 2 | 240 | 1 |
| 32 | 144 | 0 | 4 | 3 | 0.22449 | 0.204082 | 4 | 3 | 2 | 160 | 0 |
| 32 | 256 | 0 | 4 | 2 | 0.112245 | 0.0918367 | 3 | 3 | 2 | 48 | 0 |
| 48 | 36 | 0 | 4 | 4 | 0.943878 | 0.969388 | 5 | 1 | 0 | 784 | 4 |
| 48 | 64 | 0 | 4 | 4 | 0.857143 | 0.846939 | 6 | 2 | 0 | 648 | 3 |
| 48 | 144 | 1 | 4 | 4 | 0.663265 | 0.693878 | 6 | 3 | 1 | 456 | 3 |
| 48 | 256 | 0 | 4 | 4 | 0.540816 | 0.591837 | 5 | 3 | 1 | 400 | 2 |
| 64 | 36 | 0 | 4 | 4 | 1 | 1 | 4 | 0 | 0 | 784 | 4 |
| 64 | 64 | 0 | 4 | 4 | 0.994898 | 1 | 4 | 0 | 0 | 784 | 4 |
| 64 | 144 | 0 | 4 | 4 | 0.964286 | 1 | 5 | 1 | 0 | 784 | 4 |
| 64 | 256 | 1 | 4 | 4 | 0.928571 | 1 | 5 | 1 | 0 | 784 | 4 |
