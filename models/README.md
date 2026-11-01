# Model weights withheld

Neither `yolo11s-dev.pt` nor `yolo11s-blur.pt` is distributed in this snapshot, pending licensing clarification. The private checkpoints contain an Ultralytics AGPL-3.0 notice and were trained using corn1000 material licensed CC BY-NC 4.0. These facts do not by themselves settle redistribution or commercial-use rights for the weights.

Training and evaluation code remains in `src/tausendkorn/gpu/`. Measured results and limitations remain in [RESULTS.md](../docs/RESULTS.md). The blur model was trained after submission and evaluated on dev only; it is separate from the frozen benchmark.

| Private checkpoint | SHA-256 |
|---|---|
| Frozen YOLO11s dev | `7c823bf82e1ca24332e77eb08cc282a28d48bfac594bb0c3d8a0070bf5418cbc` |
| Post-submission YOLO11s blur | `7b3d0d5882b729fe0f81dea9366a42ede19260900a4d4e360cf06c0874e46f22` |

See [Ultralytics licensing](https://www.ultralytics.com/license) and [dataset attribution](../DATA_LICENSE.md). The project code is licensed AGPL-3.0-only (`../LICENSE`); that license does not cover these checkpoints.
