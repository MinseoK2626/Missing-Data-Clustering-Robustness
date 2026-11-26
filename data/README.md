# Synthetic data

Running the experiment writes the first seed's reference cohort to
`results/data/` (or the chosen output directory). All files join on `store_id`.

| File | Content |
| --- | --- |
| `complete.csv.gz` | All ten numerical features before masking |
| `profiles.csv.gz` | Separate latent store profiles for external evaluation |
| `observed.csv.gz` | The same cohort at the configured MNAR masking rate |
| `mask.csv.gz` | Boolean flag for each artificially masked cell |

A recorded product-sales zero represents a structural absence. A blank in the
observed file represents a simulated missing value and may conceal a positive
sale or a structural zero. The complete cohort and mask distinguish the two
after evaluation. Sales and transaction values use synthetic currency units.
Only the five product sales columns are eligible for masking.

The other cohorts are regenerated from the seeds and configuration in
`results/manifest.json`. See [methodology](../reports/methodology.md) for data
generation and analysis details.
