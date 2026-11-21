---
license: openrail++
base_model: layerdifforg/seethroughv0.0.2_layerdiff3d
base_model_relation: quantized
library_name: diffusers
---

# See-through: LayerDiff 3D (NF4)

A 4-bit NF4 quantisation of [layerdifforg/seethroughv0.0.2_layerdiff3d](https://huggingface.co/layerdifforg/seethroughv0.0.2_layerdiff3d) for GPUs with less memory. The
UNet and both text encoders are quantised with bitsandbytes (NF4, bfloat16
compute dtype). The VAE and the transparent VAE are unquantised and identical to
the full model.

It is used by `inference/scripts/inference_psd_quantized.py` (the default
`--quant_mode nf4`), which needs `requirements-inference-bnb.txt`. Read our
[GitHub repository](https://github.com/shitagaki-lab/see-through) for usage and details.

## Licence

The See-through code is licensed under Apache-2.0. These weights are released
under Apache-2.0 for our own contributions, and they also inherit the licences
of the models they are derived from:

- [Animagine XL 4.0](https://huggingface.co/cagliostrolab/animagine-xl-4.0) and [Stable Diffusion XL 1.0](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0): CreativeML Open RAIL++-M License
- [LayerDiffuse](https://huggingface.co/lllyasviel/LayerDiffuse_Diffusers): CreativeML Open RAIL-M License
- [SDXL-VAE-FP16-Fix](https://huggingface.co/madebyollin/sdxl-vae-fp16-fix) (the VAE): MIT License

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
