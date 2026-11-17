# Uncached and Limited-Access References

Checked: 2026-11-15. The first table lists sources not cached in the manifest. The second-pass ledger also records failed endpoints recovered through another source; those alternatives are cached explicitly.

| Source | Retrieval result | Evidence used |
| --- | --- | --- |
| [MODES 2019](https://web.cse.msu.edu/~dolsonem/pdfs/modes_paper.pdf) | Public author PDF parsed through the web service; local curl and Python clients failed TLS. Old cse.msu.edu path redirects to department HTML. | Published methods and author manuscript read; no local PDF claimed. |
| [Soros and Stanley 2014](https://wiki.santafe.edu/images/9/9c/Soros_alife14.pdf) | Local TLS retrieval failed; official UCF record says document unavailable there; old author path redirects to a missing file. | Indexed primary-text passages only. |
| [Schonfisch and de Roos 1999](https://doi.org/10.1016/S0303-2647(99)00025-8) | Direct publisher full text returned 403; no authorized public PDF verified. | Abstract/introduction/section previews only. |
| [Zhu and Szostak 2009](https://pmc.ncbi.nlm.nih.gov/articles/PMC2669828/) | Primary pages challenged on direct open; no working public PDF endpoint verified in this pass. | Relevant indexed primary Results and Discussion passages. |
| [Gibson et al. 2010](https://doi.org/10.1126/science.1190719) | Publisher retrieval restricted; no working public PDF endpoint verified in this pass. | Relevant indexed publisher passages, with recipient-cell limitation explicit. |
| [Bohm, Zhang and Dolson 2024](https://doi.org/10.1162/isal_a_00721) | Citation verified; no research text or public PDF recovered. | Next-reading lead only; no findings inferred. |

## Follow-up policy

Retry an authoritative alternate endpoint or a later restored service when the paper is needed. Preserve the version and reading-depth distinction. A search-index extract is not a downloaded PDF, and a cached PDF is not evidence that every section was read.

## Second-pass retrieval and version ledger

Checked 2026-11-15. Failed endpoints are not cached as PDFs. Original successful alternatives, exact versions, sizes, pages, and hashes are in [manifest.json](manifest.json).

| Work / endpoint | Failure or limitation | Successful alternative / evidence limit |
| --- | --- | --- |
| Varela et al. 1974, reflexus.org link | Redirected to reflexus.co, HTTP 404 | Original publisher scan recovered from Sussex institutional archive; fully read. |
| McMullin and Varela 1997, DCU index | Browser returned 502 intermittently; initial shell DNS failed in sandbox | Author PDF downloaded normally with network authorization; final revised ECAL paper, not the earlier SFI working paper. |
| Ono and Ikegami 2000, indexed CiteSeerX copy | HTTP 404 | Exact 11-page journal article recovered from the public file linked by the author's institution. The separately downloaded 1999 2D work is cached as screened-only. |
| Hutton 2007, author-linked sq3.org.uk/papers/cells2007.pdf | HTTP 404 | CiteSeerX author manuscript recovered; 32 PDF pages, not the journal's pagination. |
| DISHTINY 2022 publisher supplement endpoint | Returned article HTML, not a PDF | Main article cached. Supporting methods read in pinned author LaTeX; not verified byte-identical to publisher supplement. Code defaults differ from article decay/aging parameters; exact run configuration remains unreconciled. |
| Goldsby et al. 2012, PMC landing | Browser-verification page | Author-hosted original PDF recovered and cached for screening only. |
| Fontana and Buss 1994, author PostScript and guessed SFI landing | Web reader could not parse `.ps.gz`; guessed landing inaccessible | Original 1993 SFI working-paper PDF recovered. Later journal identity verified; detailed reading/pagination is the precursor's. A mistaken recalled DOI resolving to unrelated toxicology was rejected. |
| Dittrich and Speroni di Fenizio 2007, publisher PDF request | Redirected to abstract HTML; journal full text not recovered | Versioned 2005 short preprint read and cached. PDF body date 2021 conflicts with arXiv v1 history 2005; retained and disclosed, not silently redated. |
| BFF official CUBFF commit-history API | Inaccessible during inspection | Cached v1 paper read first. Mutable official `main` code read but not pinned; branch-count/threshold differences are observations, not a verified reproduction of v1. |
| Zhu and Szostak 2009 | Existing direct-access challenge and unrecovered PDF remain | Exact primary growth/division paper screened using earlier indexed primary-text receipts; not added to the fifteen-work second-pass corpus. |
| Levy and Miller 1998, PNAS 95:7933 (PMC20907) | Publisher and PMC PDF endpoints returned bot challenges; Europe PMC full-text XML returned HTTP 500; PMC OA service returned 404 | Abstract (p. 7933) verified through NCBI efetch; half-lives quoted from it. Arrhenius fits seen by a subagent in HTML were not used. Not cached. |
| Kaukinen et al. 2002, Nucleic Acids Res. 30:468 (PMC99829) | Same failures as above | Abstract (p. 468) verified through NCBI efetch. Not cached. |
| Robinson and Robinson 2001, PNAS 98:944 (PMC14689) | PDF not retrieved | HTML read by a subagent; no page numbers recorded. Not cached. |
| Lindahl and Nyberg 1972; Lindahl and Karlström 1973; Lindahl 1993; Radzicka and Wolfenden 1996; Ofria and Wilke 2004 | No open copy found (Ofria and Wilke: TLS failure) | Not read. Lindahl and Nyberg 1972 was seen by a subagent only as a scan inside a court filing; not used. |

Initial unprivileged shell downloads for several new sources failed DNS in the sandbox; authorized ordinary public downloads then succeeded. No paywall or authentication was bypassed. The three stream reports preserve exact queries and more detailed access receipts.
