import torch


print('PyTorch version successfully bound:', torch.__version__); 
print('Target Hardware Context:', 'CPU Engine Active' if not torch.cuda.is_available() else 'GPU Error')
