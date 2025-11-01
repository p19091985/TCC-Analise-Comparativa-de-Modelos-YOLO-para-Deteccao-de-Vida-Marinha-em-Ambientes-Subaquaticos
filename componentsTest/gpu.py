import torch

if torch.cuda.is_available():
    print("Placa NVIDIA ativa! Suporte a CUDA detectado.")
    print(f"Número de GPUs: {torch.cuda.device_count()}")
    print(f"Nome da GPU principal: {torch.cuda.get_device_name(0)}")
else:
    print("Nenhuma placa NVIDIA ativa ou suporte a CUDA não detectado.")
    print("Verifique drivers NVIDIA e instalação do CUDA.")