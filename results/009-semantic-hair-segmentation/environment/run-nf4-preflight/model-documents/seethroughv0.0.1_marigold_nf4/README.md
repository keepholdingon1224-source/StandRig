---
license: openrail++
base_model: layerdifforg/seethroughv0.0.1_marigold
base_model_relation: quantized
library_name: diffusers
---

# See-through: Marigold Depth (NF4)

A 4-bit NF4 quantisation of [layerdifforg/seethroughv0.0.1_marigold](https://huggingface.co/layerdifforg/seethroughv0.0.1_marigold) for GPUs with less memory. The
UNet and the text encoder are quantised with bitsandbytes (NF4, bfloat16 compute
dtype). The VAE is unquantised and identical to the full model.

It is used by `inference/scripts/inference_psd_quantized.py` (the default
`--quant_mode nf4`), which needs `requirements-inference-bnb.txt`. Read our
[GitHub repository](https://github.com/shitagaki-lab/see-through) for usage and details.

## Licence

The See-through code is licensed under Apache-2.0. These weights are released
under Apache-2.0 for our own contributions, and they also inherit the licences
of the models they are derived from:

- [Marigold Depth v1.1](https://huggingface.co/prs-eth/marigold-depth-v1-1) (PRS, ETH Zürich): Open RAIL++-M License
- Stable Diffusion 2 (Stability AI), the base model of Marigold: CreativeML Open RAIL++-M License. The use restrictions in its Attachment A are the ones that apply to these weights, since the Open RAIL++-M text published for Marigold leaves its own list as a placeholder.

Commercial use is permitted. The use-based restrictions in paragraph 5 and
Attachment A of the Open RAIL licences apply to every use of these weights. If
you distribute the weights or a derivative of them, or host them as a service,
you must include those restrictions as an enforceable provision in the terms
that govern that use, and tell your users about them.

The `license` field above reads `openrail++` because that licence sets the
conditions of use; our Apache-2.0 grant applies on top of it. See
[LICENSE](LICENSE) for the full terms and [NOTICE](NOTICE) for attributions and
the changes we made.

This quantised copy carries the same licence terms as the full model.

## Citation

If you find this work useful, please cite:

```bibtex
@inproceedings{lin2026seethrough,
  author={Lin, Jian and Li, Chengze and Qin, Haoyun and Chan, Kwun Wang and Jin, Yanghua and Liu, Hanyuan and Choy, Stephen Chun Wang and Liu, Xueting},
  title={See-through: Single-image Layer Decomposition for Anime Characters},
  booktitle={Proceedings of the Special Interest Group on Computer Graphics and Interactive Techniques Conference Conference Papers},
  series={SIGGRAPH Conference Papers '26},
  publisher={Association for Computing Machinery},
  address={New York, NY, USA},
  year={2026},
  pages={1--11},
  doi={10.1145/3799902.3811209},
  url={https://doi.org/10.1145/3799902.3811209}
}
```
