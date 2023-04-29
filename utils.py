import torch 
import torch.nn as nn 
from torchvision import transforms, datasets
from PIL import Image
import numpy as np
import matplotlib.pyplot as plt 
from torch.utils import data 


def clip_gradient(model, clip = 2.0):
    """Rescales norm of computed gradients.

    Parameters
    ----------
    model: nn.Module 
        Module.

    clip: float
        Maximum norm.

    """

    for p in model.parameters():
        if p.grad is not None:
            param_norm = p.grad.data.norm()
            clip_coef = clip / (param_norm + 1e-6)
            if clip_coef < 1:
                p.grad.data.mul_(clip_coef)





class MultiCropWrapper(nn.Module):
    """A class for the forward pass of all the multiple crops.
    This class assumes that all the crops are of the same shape.

    Parameters:
    -----------
    backbone: `torch.nn.Module`
            The Vision Transformer 
    """


    def __init__(self, backbone, head):
        super().__init__()
        backbone.head = nn.Identity()
        self.backbone = backbone 
        self.head = head

    def forward(self, x):
        """Run the forward pass 

        All the crops are concatenated along the batch dimension 
        and then a single forward pass is done. The final result 
        is then chuncked back to per crop tensors. 

        Parameters:
        -----------
        x: list 
        list of 'torch.Tensor' each of shape (n_samples, 3, size, size).

        Returns
        -------
        tuple 
            Tuple of 'torch.Tensor' each of shape '(n_samples, out_dim)'
        """

        n_crops = len(x)
        concatenated = torch.cat(x, dim = 0) # (n_samples * n_crops, in_dim)
        cls_token = self.backbone(concatenated) #(n_samples * n_crops, out_dim)
        logits = self.head(cls_token) #(n_samples * n_crops, out_dim)
        chunks = logits.chunk(n_crops) #List: n_crops, (n_samples, out_dim)

        return chunks 




class DataAugmentation(object):


    def __init__(self, global_crops_scale = (0.4, 1), local_crops_scale = (0.1, 0.4), n_local_crops = 8, size = 32):
        self.n_local_crops = n_local_crops

        RandomGaussianBlur = lambda p: transforms.RandomApply([transforms.GaussianBlur(kernel_size = 5, sigma = (0.1, 2))], p = p)

        flip_and_jitter = transforms.Compose([
            transforms.RandomHorizontalFlip(p = 0.5), #0.5
            transforms.RandomApply([
                transforms.ColorJitter(brightness = 0.4, contrast = 0.4, saturation=0.2, hue=.1)], p = 0.8), #0.8

            transforms.RandomGrayscale(p = 0.2) 
            ])


        normalize = transforms.Compose([
            transforms.ToTensor(), 
            transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225))
            ])


        self.global1 = transforms.Compose([
            #transforms.Resize(size = 224),                                  
            transforms.RandomResizedCrop(size, scale = global_crops_scale, interpolation = transforms.InterpolationMode.BICUBIC),  
            flip_and_jitter, 
            RandomGaussianBlur(p = 0.1),
            normalize
            ])

        #Differnce w/ global1: 1) Here p global is much lower 2) Here we use solarization. 
        self.global2 = transforms.Compose([
            #transforms.Resize(size = 224),                                    
            transforms.RandomResizedCrop(size, scale = global_crops_scale, interpolation =  transforms.InterpolationMode.BICUBIC),
            flip_and_jitter, 
            RandomGaussianBlur(p = 0.1),
            transforms.RandomSolarize(170, p = 0.2),
            normalize
            ])


        self.local =  transforms.Compose([
            #transforms.Resize(size = 224),                                   
            transforms.RandomResizedCrop(size, scale = local_crops_scale, interpolation = transforms.InterpolationMode.BICUBIC),
            flip_and_jitter, 
            RandomGaussianBlur(0.1),
            normalize
            ])



    def __call__(self, img):
        """ Apply transformation.

        Parameters
        ----------
        img: PIL.Image
            input image

        Returns
        -------
        all_crops: list
            list of 'torch.Tensor' representing different views of the input 'img'		
        """

        all_crops = []
        all_crops.append(self.global1(img))
        all_crops.append(self.global2(img))

        all_crops.extend([self.local(img) for _ in range(self.n_local_crops)])

        return all_crops




if __name__ == '__main__':
    from main import hello 

    hello()
