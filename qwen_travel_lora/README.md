# Adaptador LoRA

El adaptador LoRA fue entrenado en Google Colab durante el experimento documentado
en `Deivy_G_GenAI_U1.ipynb`.

El archivo binario `adapter_model.safetensors` no se incluye en este repositorio.
Para reproducir la variante híbrida Qwen + LoRA, ejecute las celdas de fine-tuning
del notebook y guarde el adaptador en esta carpeta.

La aplicación también puede ejecutarse sin el adaptador; en ese caso utiliza el
modelo base Qwen2.5 junto con RAG estructurado y validación determinista.
