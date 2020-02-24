import jax.numpy as np
import math
PI = math.pi
class LossFunction:

	def __init__(self,surface,coil_set):
		self.surface = surface
		self.coil_set = coil_set


	def bnsquared(self):
		""" 

		Computes 1/2(B dot n)^2 dA over the surface from the coils, but doesn't sum over the entire surface yet. 
			
		Requires: A CoilSet and a Surface, as method variables.
		
		Returns: A N_zeta by N_theta array which computes 1/2(B dot n)^2 dA at each point on the surface. 
		We can eventually sum over this array to get the total integral over the surface. 

		"""
		mu_0 = 1. 
		r = self.surface.get_r_central() # NZ x NT x 3
		mu_0I = self.coil_set.get_I() * mu_0 / (self.coil_set.NNR * self.coil_set.NBR) # NC
		dl = self.coil_set.get_dl() # NC x NS x NNR x NBR x 3
		l = self.coil_set.get_r_middle()  # NC x NS x NNR x NBR x 3
		mu_0Idl = mu_0I[:,np.newaxis,np.newaxis,np.newaxis,np.newaxis] * dl # NC x NS x NNR x NBR x 3
		r_minus_l = r[np.newaxis,:,:,np.newaxis,np.newaxis,np.newaxis,:] - l[:,np.newaxis,np.newaxis,:,:,:,:] # NC x NZ x NT x NS x NNR x NBR x 3
		top = np.cross(mu_0Idl[:,np.newaxis,np.newaxis, :,:,:,:],r_minus_l) # NC x NZ x NT x NS x NNR x NBR x 3
		bottom = np.linalg.norm(r_minus_l,axis=-1)**3 # NC x NZ x NT x NS x NNR x NBR

		B = np.sum(top / bottom[:,:,:,:,:,:,np.newaxis], axis=(0,3,4,5)) # NZ x NT x 3
		nn = self.surface.get_nn() # NZ x NT x 3
		C = .5 * 4 * PI**2 / (self.surface.NT * self.surface.NZ)
		return np.sum(nn * B, axis=-1)**2 * self.surface.get_sg() * C #NZ x NT 



