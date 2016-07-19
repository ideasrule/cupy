import itertools
import numpy
import six

from chainer import cuda
from chainer.utils.conv import get_conv_outsize
from chainer.utils import conv_nd_kernel


def as_tuple(x, n):
    if hasattr(x, '__getitem__'):
        assert len(x) == n
        return tuple(x)
    return (x,) * n


def im2col_nd_cpu(img, ksize, stride, pad, pval=0, cover_all=False):
    # Assured consistency of dimensions of parameters by caller.
    n, c = img.shape[0:2]       # (n, c, d_1, d_2, ..., d_N)
    dims = img.shape[2:]
    outs = tuple(get_conv_outsize(d, k, s, p, cover_all)
                 for (d, k, s, p) in zip(dims, ksize, stride, pad))

    # Pad around image.
    pad_width = ((0, 0), (0, 0)) + tuple(
        (p, p + s - 1) for (s, p) in zip(stride, pad))
    img = numpy.pad(img, pad_width, mode='constant', constant_values=(pval,))

    # Make patch array with which we will compute correlation with filter.
    # shape: (n, c, k_1, k_2, ..., k_N, out_1, out_2, ..., out_N)
    shape = (n, c) + ksize + outs
    col = numpy.ndarray(shape, dtype=img.dtype)

    # Fill the patch array.
    ndim = len(dims)
    colon = slice(None)
    for kxs in itertools.product(*[six.moves.range(k) for k in ksize]):
        # col[:, :, kx_1, kx_2, ..., kx_N, :, :, ..., :]
        col_index = (colon, colon) + kxs + (colon,) * ndim
        # img[:, :, kx_1:kx_lim_1:s_1, ..., kx_N:kx_lim_N:s_N]
        kx_lims = tuple(kx + s * out
                        for (kx, s, out) in zip(kxs, stride, outs))
        img_index = (colon, colon) + tuple(
            slice(kx, kx_lim, s)
            for (kx, kx_lim, s) in zip(kxs, kx_lims, stride))
        col[col_index] = img[img_index]

    return col


_im2col_cache = {}


def im2col_nd_gpu(img, ksize, stride, pad, cover_all=False):
    # Assured consistency of dimensions of parameters by caller.
    n, c = img.shape[0:2]       # (n, c, d_1, d_2, ..., d_N)
    dims = img.shape[2:]
    ndim = len(dims)
    outs = tuple(get_conv_outsize(d, k, s, p, cover_all)
                 for (d, k, s, p) in zip(dims, ksize, stride, pad))

    # col_shape: (n, c, k_1, k_2, ..., k_N, out_1, out_2, ..., out_N)
    shape = (n, c) + ksize + outs
    col = cuda.empty(shape, dtype=img.dtype)

    if ndim not in _im2col_cache:
        _im2col_cache[ndim] = conv_nd_kernel.Im2colNDKernel(ndim).generate()
    in_params, out_params, operation, name = _im2col_cache[ndim]

    cuda.elementwise(in_params, out_params, operation, name)(
        img.reduced_view(), *(dims + outs + ksize + stride + pad + (col,)))

    return col


def col2im_nd_cpu(col, stride, pad, dims):
    # Assured consistency of dimensions of parameters by caller.
    n, c = col.shape[:2]  # (n, c, kx_1, ..., kx_N, out_1, ..., out_N)
    mid = (len(col.shape) - 2) // 2 + 2
    ksize = col.shape[2:mid]
    outs = col.shape[mid:]
    colon = slice(None)

    # Image with padded size.
    img_shape = (n, c) + tuple(d + 2 * p + s - 1
                               for (d, p, s) in zip(dims, pad, stride))
    img = numpy.zeros(img_shape, dtype=col.dtype)
    for kxs in itertools.product(*[six.moves.range(k) for k in ksize]):
        # (:, :, kx_1:kx_lim_1:s_1, ..., kx_N:kx_lim_N:s_N)
        kx_lims = tuple(kx + s * out
                        for (kx, s, out) in zip(kxs, stride, outs))
        img_index = (colon, colon) + tuple(
            slice(kx, kx_lim, s)
            for (kx, kx_lim, s) in zip(kxs, kx_lims, stride))
        # (:, :, kx_1, kx_2, ..., kx_N, :, :, ..., :)
        col_index = (colon, colon) + kxs + (colon,) * len(outs)
        img[img_index] += col[col_index]

    # (:, :, p_1:d_1 + p_1, p_2:d_2 + p_2, ..., p_N:d_N + p_N]
    img_index = (colon, colon) + tuple(
        slice(p, d + p) for (p, d) in zip(pad, dims))
    return img[img_index]


_col2im_cache = {}


def col2im_nd_gpu(col, stride, pad, dims):
    # Assured consistency of dimensions of parameters by caller.
    n, c = col.shape[:2]        # (n, c, k_1, ..., k_N, out_1, ..., out_N)
    mid = (len(col.shape) - 2) // 2 + 2
    ksize = col.shape[2:mid]
    outs = col.shape[mid:]
    ndim = len(dims)

    img_shape = (n, c) + dims   # (n, c, d_1, d_2, ..., d_N)
    img = cuda.empty(img_shape, dtype=col.dtype)

    if ndim not in _col2im_cache:
        _col2im_cache[ndim] = conv_nd_kernel.Col2imNDKernel(ndim).generate()
    in_params, out_params, operation, name = _col2im_cache[ndim]

    cuda.elementwise(in_params, out_params, operation, name)(
        col.reduced_view(), *(dims + outs + ksize + stride + pad + (img,)))

    return img
