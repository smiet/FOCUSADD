import argparse
import time
from surface.readAxis import readAxis
from surface.Surface import Surface
from surface.Axis import Axis
from coils.CoilSet import CoilSet
import jax.numpy as np
import numpy as numpy
from lossFunctions.DefaultLoss import default_loss
import math
import csv
from functools import partial
import jax.experimental.optimizers as op
from jax import value_and_grad, jit


# from jax.config import config
# config.update("jax_enable_x64",True)


PI = math.pi


def args_to_op(optimizer_string, lr, mom=0.9):
    return {
        "gd": lambda lr, _: op.sgd(lr),
        "sgd": lambda lr, _: op.sgd(lr),
        "GD": lambda lr, _: op.sgd(lr),
        "SGD": lambda lr, _: op.sgd(lr),
        "momentum": lambda lr, mom: op.momentum(lr, mom),
    }[optimizer_string](lr, mom)


def set_args():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "-n",
        "--num_iter",
        help="Number of iterations by the optimizer",
        default=10,
        type=int,
    )
    parser.add_argument(
        "-nt",
        "--num_theta",
        help="Number of gridpoints in theta (poloidal angle) on the magnetic surface",
        default=32,
        type=int,
    )
    parser.add_argument(
        "-nz",
        "--num_zeta",
        help="Number of gridpoints in zeta (toroidal angle) on the magnetic surface",
        default=64,
        type=int,
    )
    parser.add_argument(
        "-nc", "--num_coils", help="Number of coils", default=8, type=int
    )
    parser.add_argument(
        "-ns",
        "--num_segments",
        help="Number of segments in each coil",
        default=32,
        type=int,
    )
    parser.add_argument(
        "-nfc",
        "--num_fourier_coils",
        help="Number of Fourier Components describing each coil",
        default=4,
        type=int,
    )
    parser.add_argument(
        "-nnr",
        "--num_normal_rotate",
        help="Number of filaments in the (rotated) normal direction for each multi-build coil",
        default=1,
        type=int,
    )
    parser.add_argument(
        "-nbr",
        "--num_binormal_rotate",
        help="Number of filaments in the (rotated) binormal direction for each multi-build coil",
        default=1,
        type=int,
    )
    parser.add_argument(
        "-nfr",
        "--num_fourier_rotate",
        help="Number of Fourier Components describing the rotation relative to the torsion vector of each coil",
        default=0,
        type=int,
    )
    parser.add_argument(
        "-ln",
        "--length_normal",
        help="Length between each coil in the (rotated) normal direction",
        default=0.01,
        type=float,
    )
    parser.add_argument(
        "-lb",
        "--length_binormal",
        help="Length between each coil in the (rotated) binormal direction",
        default=0.01,
        type=float,
    )
    parser.add_argument(
        "-rc", "--radius_coil", help="Radius of coils", default=2.0, type=float
    )
    parser.add_argument(
        "-rs", "--radius_surface", help="Radius of surface", default=1.0, type=float
    )
    parser.add_argument(
        "-nr",
        "--num_rotate",
        help="Number of rotations of each finite-build coil",
        default=0,
        type=int,
    )
    parser.add_argument(
        "-lr",
        "--learning_rate",
        help="Learning Rate of SGD, ODEFlow, Newtons Method",
        default=0.0001,
        type=float,
    )
    parser.add_argument(
        "-o",
        "--output_file",
        help="Name of output file for coils",
        default="simpleTest",
        type=str,
    )
    parser.add_argument(
        "-i", "--input_file", help="Name of input file for coils", default=None, type=str
    )
    parser.add_argument(
        "-w",
        "--weight_length",
        help="Length of weight paid to coils",
        default=0.1,
        type=float,
    )
    parser.add_argument(
        "-a", "--axis", help="Name of axis file", default="defaultAxis", type=str
    )
    parser.add_argument(
        "-op",
        "--optimizer",
        help="Name of optimizer. Either SGD, GD (same) or Momentum",
        default="GD",
        type=str,
    )
    parser.add_argument(
        "-mom",
        "--momentum_mass",
        help="Momentum mass parameter.",
        default=0.9,
        type=float,
    )
    return parser.parse_args()


def create_args_dict(args):
    args_dict = {}
    args_dict["numCoils"] = args.num_coils
    args_dict["numSegments"] = args.num_segments
    args_dict["numFourierCoils"] = args.num_fourier_coils
    args_dict["numFourierRotate"] = args.num_fourier_rotate
    args_dict["lengthNormal"] = args.length_normal
    args_dict["lengthBinormal"] = args.length_binormal
    args_dict["numNormalRotate"] = args.num_normal_rotate
    args_dict["numBinormalRotate"] = args.num_binormal_rotate
    args_dict["radiusCoil"] = args.radius_coil
    args_dict["numRotate"] = args.num_rotate
    return args_dict


def update(i, opt_state, get_params, opt_update, loss):
    params = get_params(opt_state)
    loss_val, gradient = value_and_grad(loss)(params)
    return opt_update(i, gradient, opt_state), loss_val


def main():
    args = set_args()
    args_dict = create_args_dict(args)
    input_file = args.input_file
    output_file = args.output_file

    surface = Surface(
        "./initFiles/axes/{}.txt".format(args.axis),
        args.num_zeta,
        args.num_theta,
        args.radius_surface,
    )

    if input_file is not None:
        coilSet = CoilSet(surface, input_file="coils/saved/{}.hdf5".format(input_file))
    else:
        coilSet = CoilSet(surface, args_dict=args_dict)

    loss_func = partial(default_loss, surface, coilSet, args.weight_length)

    opt_init, opt_update, get_params = args_to_op(
        args.optimizer, args.learning_rate, args.momentum_mass
    )
    opt_state = opt_init(coilSet.get_params())

    loss_vals = []
    start = time.time()

    for i in range(args.num_iter):
        opt_state, loss_val = update(i, opt_state, get_params, opt_update, loss_func)
        params = get_params(opt_state)
        loss_vals.append(loss_val)
        print(loss_val)

    end = time.time()
    print(end - start)
    with open("{}.txt".format(output_file), "w") as f:
        wr = csv.writer(f, quoting=csv.QUOTE_ALL)
        wr.writerow(loss_vals)

    coilSet.set_params(params)
    coilSet.write("{}.hdf5".format(output_file))


if __name__ == "__main__":
    main()
