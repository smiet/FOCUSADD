import jax.numpy as np
from jax.experimental.ode import odeint
from functools import partial
from jax.config import config
import jax
from jax import jit
import matplotlib.pyplot as plt
import sys
import time
sys.path.append("..")

from surface.Surface import Surface
from coils.CoilSet import CoilSet
config.update("jax_enable_x64", True)


PI = np.pi

class Poincare():

	def computeB(I, dl, l, r, zeta, z):
		"""
			Inputs:

			r, zeta, z : The coordinates of the point we want the magnetic field at. Cylindrical coordinates.

			Outputs: 

			B_z, B_zeta, B_z : the magnetic field components at the input coordinates created by the currents in the coils. Cylindrical coordinates.
		"""
		x = r * np.cos(zeta)
		y = r * np.sin(zeta)
		xyz = np.asarray([x,y,z])
		
		mu_0 = 1. 
		mu_0I = I * mu_0 # NC
		mu_0Idl = mu_0I[:,np.newaxis,np.newaxis,np.newaxis,np.newaxis] * dl # NC x NS x NNR x NBR x 3
		r_minus_l = xyz[np.newaxis,np.newaxis,np.newaxis,np.newaxis,:] - l[:,:,:,:,:] # NC x NS x NNR x NBR x 3
		top = np.cross(mu_0Idl,r_minus_l) # NC x x NS x NNR x NBR x 3
		bottom = np.linalg.norm(r_minus_l,axis=-1)**3 # NC x NS x NNR x NBR
		B_xyz = np.sum(top / bottom[:,:,:,:,np.newaxis], axis=(0,1,2,3)) # 3, xyz coordinates
		B_x = B_xyz[0]
		B_y = B_xyz[1]
		B_z = B_xyz[2]
		B_r = B_x * np.cos(zeta) + B_y * np.sin(zeta)
		B_zeta = - B_x * np.sin(zeta) + B_y * np.cos(zeta)
		return B_r, B_zeta, B_z

	def step(B_func, arr, zeta):
		r = arr[0]
		z = arr[1]
		B_r, B_zeta, B_z = B_func(r, zeta, z) 
		Fr = (B_r * r / B_zeta)
		Fz = (B_z * r / B_zeta)
		return np.asarray((Fr, Fz))


	def getPoincarePoints(N_poincare, zeta, radii, surface, is_frenet, coil_data, coil_params):
		"""

			NOTE: THIS ONLY WORKS FOR zeta = 0 RIGHT NOW

			Loop over N_poincare points in the plot, equally spaced in toroidal
			radius starting from the magnetic axis at a given zeta, and 
			creating a list of points where the plot punctures.

			Inputs:

			N_poincare : number of times we puncture the poincare plot, starting at radius r
			zeta : Which zeta will our poincare plot track? We are getting a poloidal cross-section at zeta.
			radii : list of radii r which we start at, away from our magnetic axis. We expect this to range from 0 
			to slightly higher than 1. 

			Outputs:

			rs, zs : lists of floating point numbers where the field lines intersect at a given zeta. 

		"""

		axis = surface.get_axis()
		x_axis, y_axis, z_axis = axis.get_r_from_zeta(zeta)
		r_axis = np.sqrt(x_axis ** 2 + y_axis ** 2)
		v1, _ = axis.get_frame()
		v1 = v1[0, :] # at zeta = 0 THIS LINE BREAKS THE CODE
		ep = axis.epsilon
		saep = axis.a * surface.s * np.sqrt(ep)
		ct = np.cos(zeta)
		st = np.sin(zeta)

		rs = np.asarray([])
		zs = np.asarray([])
		I, dl, r, _ = CoilSet.get_outputs(coil_data, coil_params)
		B_func = partial(Poincare.computeB, I, dl, r)
		step_partial = jit(partial(Poincare.step, B_func))
		t_eval = np.linspace(0, 2 * PI * N_poincare, N_poincare + 1)

		@jit
		def update(r):
			v1_normalized = r * saep * v1
			y = np.asarray((r_axis + ct * v1_normalized[0] + st * v1_normalized[1], z_axis + v1_normalized[2]))
			sol = odeint(step_partial, y, t_eval)
			return sol[:, 0], sol[:, 1]


		for r in radii:
			print(r)
			r_new, z_new = update(r)
			rs = np.concatenate((rs, r_new))
			zs = np.concatenate((zs, z_new))

		return rs, zs



def main():
	surface = Surface("../initFiles/axes/ellipticalAxis4Rotate.txt", 128, 32, 1.0)

	radii = np.linspace(0.0,1.11111111,15)

	start = time.time()

	N = 100
	coil_data, coil_params = CoilSet.get_initial_data(surface, input_file="../../tests/postresaxis/triple_comparison/fb.hdf5")
	rs, zs = Poincare.getPoincarePoints(N, 0.0, radii, surface, False, coil_data, coil_params)

	end = time.time()
	print(end - start)


	"""
	font = {'family' : 'serif',
        'weight' : 'normal',
        'size'   : 12}

	plt.rc('font', **font)

	plt.plot(rs,zs,'ko', markersize=0.5, color='blue')
	plt.xlabel("R [m]")
	plt.ylabel("Z [m]")
	plt.show()
	"""

	np.save("rs.npy", rs)
	np.save("zs.npy", zs)

if __name__ == "__main__":
	main()
