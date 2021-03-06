from .LossFunction import LossFunction
import jax.numpy as np
import math
from functools import partial
from jax import jit

PI = math.pi 
class SaddleLoss(LossFunction):


	def __init__(self,surface,saddle_coil_set,weight_length=0.01):
		super().__init__(surface,saddle_coil_set) # call this with self.coil_set
		self.weight_length = weight_length
		self.B_t = SaddleLoss.biot_savart_toroidal(self.surface.get_r_central())

	@jit
	def bn_squared_saddle(r, B_t, I_s, dl_s, l_s, nn, sg):
		""" 

		Computes 1/2(B dot n)^2 dA over the surface from the coils, but doesn't sum over the entire surface yet. 
			
		Inputs:

		r : Position we want to evaluate at, NZ x NT x 3
		I_t : Current in ith coil, length NC, TOROIDAL
		dl_t : Vector which has coil segment length and direction, NC x NS x 3, TOROIDAL
		l_t : Positions of center of each coil segment, NC x NS x 3, TOROIDAL
		I_s : Current in ith coil, length NC, SADDLE
		dl_s : Vector which has coil segment length and direction, NC x NS x 3, SADDLE
		l_s : Positions of center of each coil segment, NC x NS x 3, SADDLE
		nn : Normal vector on the surface, NZ x NT x 3
		sg : Area of the surface, 
		
		Returns: 

		A NZ x NT array which computes 1/2(B dot n)^2 dA at each point on the surface. 
		We can eventually sum over this array to get the total integral over the surface. I choose not to
		sum so that we can compute gradients of the surface magnetic normal if we'd like. 

		"""
		B = B_t + SaddleLoss.biot_savart_saddle(r,I_s,dl_s,l_s)   # NZ x NT x 3
		#B = SaddleLoss.biot_savart_saddle(r,I_t,dl_t,l_t) + SaddleLoss.biot_savart_saddle(r,I_s,dl_s,l_s)   # NZ x NT x 3
		return .5 * np.sum(nn * B, axis=-1)**2 * sg #NZ x NT 

	@jit
	def biot_savart_toroidal(r, I=1.0, NC_t = 16.0):
		"""
		Assumes the toroidal coils are a single infinitely long current at the 
		center of the device, so B = mu_0 I / 2 pi r. Since I set mu_0/4pi = 1
		in biot_savart_saddle, I'll use B = 2 I / r here, where the direction
		is in the phi-direction in cylindrical coordinates. 

		Inputs:

		r: NZ x NT x 3, the position of the points on the surface
		I: float, describing the total toroidal current. I rescale this
		to match the current per length of a solenoid with NC_t toroidal
		coils per axis length, which is about 2pi. 


		"""
		mag_r = np.sqrt(r[:,:,0]**2 + r[:,:,1]**2)

		B_phi = 2.0 * (I * NC_t / (2.0 * PI)) / mag_r
		cos_theta = r[:,:,0] / mag_r
		sin_theta = r[:,:,1] / mag_r
		B_x = - B_phi * sin_theta
		B_y = B_phi * cos_theta
		B_z = np.zeros((r.shape[0],r.shape[1]))
		return np.stack((B_x,B_y,B_z),axis=-1)



	@jit
	def biot_savart_saddle(r, I, dl, l):
		"""
		Inputs:

		r : Position we want to evaluate at, NZ x NT x 3
		I : Current in ith coil, length NC
		dl : Vector which has coil segment length and direction, NC x NS x 3
		l : Positions of center of each coil segment, NC x NS x 3

		Returns: 

		A NZ x NT x 3 array which is the magnetic field vector on the surface points 
		"""
		mu_0 = 1.
		mu_0I = I * mu_0
		mu_0Idl = mu_0I[:,np.newaxis,np.newaxis] * dl # NC x NS x 3
		r_minus_l = r[np.newaxis,:,:,np.newaxis,:] - l[:,np.newaxis,np.newaxis,:,:] # NC x NZ x NT x NS x 3
		top = np.cross(mu_0Idl[:,np.newaxis,np.newaxis,:,:],r_minus_l) # NC x NZ x NT x NS x 3
		bottom = np.linalg.norm(r_minus_l,axis=-1)**3 # NC x NZ x NT x NS
		B = np.sum(top / bottom[:,:,:,:,np.newaxis], axis=(0,3)) # NZ x NT x 3
		return B

	def loss(self,params):
		self.coil_set.set_params(params)
		B_loss_val = np.sum(SaddleLoss.bn_squared_saddle(self.surface.get_r_central(),\
			self.B_t,\
			self.coil_set.get_I_s(), self.coil_set.get_dl_s(), self.coil_set.get_r_s_middle(),\
			self.surface.get_nn(), self.surface.get_sg()))

		len_loss_val = self.coil_set.get_saddle_length()
		return B_loss_val + self.weight_length * len_loss_val