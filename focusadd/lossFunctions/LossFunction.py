import jax.numpy as np
from jax import jit
import math

# from memory_profiler import profile
PI = math.pi


class LossFunction:
    @jit
    def quadratic_flux(r, I, dl, l, nn, sg, B_extern = None):
        """ 

		Computes the normalized quadratic flux over the whole surface.
			
		Inputs:

		r : Position we want to evaluate at, NZ x NT x 3
		I : Current in ith coil, length NC
		dl : Vector which has coil segment length and direction, NC x NS x NNR x NBR x 3
		l : Positions of center of each coil segment, NC x NS x NNR x NBR x 3
		nn : Normal vector on the surface, NZ x NT x 3
		sg : Area of the surface, 
		
		Returns: 

		A NZ x NT array which computes integral of 1/2(B dot n)^2 dA / integral of B^2 dA. 
		We can eventually sum over this array to get the total integral over the surface. I choose not to
		sum so that we can compute gradients of the surface magnetic normal if we'd like. 

		"""
        B = LossFunction.biotSavart(r, I, dl, l)  # NZ x NT x 3
        if B_extern is not None:
            B = B + B_extern
        return (
            0.5
            * np.sum(np.sum(nn * B, axis=-1) ** 2 * sg)
        )  # NZ x NT

    @jit
    def biotSavart(r, I, dl, l):
        """
		Inputs:

		r : Position we want to evaluate at, NZ x NT x 3
		I : Current in ith coil, length NC
		dl : Vector which has coil segment length and direction, NC x NS x NNR x NBR x 3
		l : Positions of center of each coil segment, NC x NS x NNR x NBR x 3

		Returns: 

		A NZ x NT x 3 array which is the magnetic field vector on the surface points 
		"""
        mu_0 = 1.0
        mu_0I = I * mu_0
        mu_0Idl = (
            mu_0I[:, np.newaxis, np.newaxis, np.newaxis, np.newaxis] * dl
        )  # NC x NS x NNR x NBR x 3
        r_minus_l = (
            r[np.newaxis, :, :, np.newaxis, np.newaxis, np.newaxis, :]
            - l[:, np.newaxis, np.newaxis, :, :, :, :]
        )  # NC x NZ x NT x NS x NNR x NBR x 3
        top = np.cross(
            mu_0Idl[:, np.newaxis, np.newaxis, :, :, :, :], r_minus_l
        )  # NC x NZ x NT x NS x NNR x NBR x 3
        bottom = (
            np.linalg.norm(r_minus_l, axis=-1) ** 3
        )  # NC x NZ x NT x NS x NNR x NBR
        B = np.sum(
            top / bottom[:, :, :, :, :, :, np.newaxis], axis=(0, 3, 4, 5)
        )  # NZ x NT x 3
        return B

    @jit
    def normalized_error(r, I, dl, l, nn, sg, B_extern = None):
        B = LossFunction.biotSavart(r, I, dl, l)  # NZ x NT x 3
        if B_extern is not None:
            B = B + B_extern

        B_n = np.abs( np.sum(nn * B, axis=-1) )
        B_mag = np.linalg.norm(B, axis=-1)
        A = np.sum(sg)

        return np.sum( (B_n / B_mag) * sg ) / A
