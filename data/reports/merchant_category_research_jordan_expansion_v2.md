# Merchant-category research comparison

Merchant names only. No active engine change or final test inference. Softmax scores are uncalibrated.

| Variant | Training businesses | Name forms | Human validation correct / answered / total | Combined research-label validation correct / answered / total |
| --- | ---: | ---: | --- | --- |
| baseline | 156 | 156 | 1 / 1 / 5 | 8 / 11 / 28 |
| aliases | 156 | 209 | 1 / 1 / 5 | 8 / 11 / 28 |
| augmented | 156 | 350 | 1 / 1 / 5 | 8 / 11 / 28 |

Selected research variant: **baseline**. Ties retain the canonical-name baseline. Selection uses only human validation answers and fixed thresholds.

Assistant-label agreement is a research diagnostic, not independent accuracy. Five human validation businesses are insufficient to establish calibrated confidence or broad generalization. 3 target categories have no training businesses; low-support or weak-evidence predictions abstain. The active SMS engine is unchanged.

Normalization preserves merchant prefixes such as LC Waikiki; it uses the shared digit helper but has its own versioned name-feature contract. Python and standalone TypeScript scoring share this contract. Models use flat feature-major weights and require no external ML runtime.

Synthetic spelling/spacing forms are generated only in memory for fitting and documented once in the JSON report. They inherit existing labels, are capped at one per eligible training business, and keep each business's total weight equal. They are not new merchants or observed bank descriptors.
