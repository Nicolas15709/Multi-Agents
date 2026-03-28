# Model routing

Estado actual:
- Premium / tareas importantes: `openai-codex/gpt-5.4`
- Local / fallback ligero: `ollama/qwen2.5:7b`
- Gemini CLI: pendiente de configurar con una cuenta secundaria

Uso recomendado:
- Preguntas simples o pruebas locales: `ollama/qwen2.5:7b`
- Tareas complejas, delicadas o importantes: `openai-codex/gpt-5.4`
- Cuando se añada Gemini con cuenta secundaria: usarlo para preguntas ligeras cloud

Notas:
- Qwen 7B ocupa ~4.7 GB en Ollama.
- En esta máquina (4 CPU ARM, 23 GiB RAM, sin GPU) es usable, pero más lento que cloud.
- Si el modelo no aparece en OpenClaw, reiniciar Gateway para que refresque el catálogo de Ollama.
