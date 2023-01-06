from cupyx.scipy.interpolate import pade
from cupy import allclose, array_equal, array


def test_pade_trivial():
    nump, denomp = pade(array([1.0]), 0)
    assert allclose(nump.c, [1.0])
    assert allclose(denomp.c, [1.0])

    nump, denomp = pade(array([1.0]), 0, 0)
    assert allclose(nump.c, [1.0])
    assert allclose(denomp.c, [1.0])


def test_pade_4term_exp():
    # First four Taylor coefficients of exp(x).
    # Unlike poly1d, the first array element is the zero-order term.
    an = array([1.0, 1.0, 0.5, 1.0/6])

    nump, denomp = pade(an, 0)
    assert allclose(nump.c, [1.0/6, 0.5, 1.0, 1.0])
    assert allclose(denomp.c, [1.0])

    nump, denomp = pade(an, 1)
    assert allclose(nump.c, [1.0/6, 2.0/3, 1.0])
    assert allclose(denomp.c, [-1.0/3, 1.0])

    nump, denomp = pade(an, 2)
    assert allclose(nump.c, [1.0/3, 1.0])
    assert allclose(denomp.c, [1.0/6, -2.0/3, 1.0])

    nump, denomp = pade(an, 3)
    assert allclose(nump.c, [1.0])
    assert allclose(denomp.c, [-1.0/6, 0.5, -1.0, 1.0])

    # Testing inclusion of optional parameter
    nump, denomp = pade(an, 0, 3)
    assert allclose(nump.c, [1.0/6, 0.5, 1.0, 1.0])
    assert allclose(denomp.c, [1.0])

    nump, denomp = pade(an, 1, 2)
    assert allclose(nump.c, [1.0/6, 2.0/3, 1.0])
    assert allclose(denomp.c, [-1.0/3, 1.0])

    nump, denomp = pade(an, 2, 1)
    assert allclose(nump.c, [1.0/3, 1.0])
    assert allclose(denomp.c, [1.0/6, -2.0/3, 1.0])

    nump, denomp = pade(an, 3, 0)
    assert allclose(nump.c, [1.0])
    assert allclose(denomp.c, [-1.0/6, 0.5, -1.0, 1.0])

    # Testing reducing array.
    nump, denomp = pade(an, 0, 2)
    assert allclose(nump.c, [0.5, 1.0, 1.0])
    assert allclose(denomp.c, [1.0])

    nump, denomp = pade(an, 1, 1)
    assert allclose(nump.c, [1.0/2, 1.0])
    assert allclose(denomp.c, [-1.0/2, 1.0])

    nump, denomp = pade(an, 2, 0)
    assert allclose(nump.c, [1.0])
    assert allclose(denomp.c, [1.0/2, -1.0, 1.0])


def test_pade_ints():
    # Simple test sequences (one of ints, one of floats).
    an_int = array([1, 2, 3, 4])
    an_flt = array([1.0, 2.0, 3.0, 4.0])

    # Make sure integer arrays give the same result as float arrays with same
    # values.
    for i in range(0, len(an_int)):
        for j in range(0, len(an_int) - i):

            # Create float and int pade approximation for given order.
            nump_int, denomp_int = pade(an_int, i, j)
            nump_flt, denomp_flt = pade(an_flt, i, j)

            # Check that they are the same.
            assert array_equal(nump_int.c, nump_flt.c)
            assert array_equal(denomp_int.c, denomp_flt.c)


def test_pade_complex():
    # Test sequence with known solutions - see page 6 of
    # 10.1109/PESGM.2012.6344759.
    # Variable x is parameter - these tests will work with any complex number.
    x = 0.2 + 0.6j
    an = array([1.0, x, -x*x.conjugate(),
                x.conjugate()*(x**2) + x*(x.conjugate()**2),
                -(x**3)*x.conjugate() - 3 *
                (x*x.conjugate())**2 - x*(x.conjugate()**3)
                ])

    nump, denomp = pade(an, 1, 1)
    assert allclose(nump.c, [x + x.conjugate(), 1.0])
    assert allclose(denomp.c, [x.conjugate(), 1.0])

    nump, denomp = pade(an, 1, 2)
    assert allclose(nump.c, [x**2, 2*x + x.conjugate(), 1.0])
    assert allclose(denomp.c, [x + x.conjugate(), 1.0])

    nump, denomp = pade(an, 2, 2)
    assert allclose(nump.c, [x**2 + x*x.conjugate() +
                             x.conjugate()**2, 2*(x + x.conjugate()), 1.0])
    assert allclose(denomp.c, [x.conjugate()**2, x + 2*x.conjugate(), 1.0])