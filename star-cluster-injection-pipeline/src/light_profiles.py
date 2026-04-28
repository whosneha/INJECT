import numpy as np


# ---------------------------------------------------------------------------
# Flux utility
# ---------------------------------------------------------------------------

def mag_to_flux(magnitude, zero_point=27.0):
    """Convert AB magnitude to counts using the given zero point."""
    return 10.0 ** ((zero_point - magnitude) / 2.5)


def flux_to_mag(flux, zero_point=27.0):
    """Convert counts to AB magnitude."""
    return zero_point - 2.5 * np.log10(np.clip(flux, 1e-30, None))


# ---------------------------------------------------------------------------
# Base class
# ---------------------------------------------------------------------------

class BaseProfile:
    """
    Base class for all cluster light profiles.

    Subclasses must implement `surface_brightness(r)`.
    `generate_2d` is provided here and works for all subclasses.
    """

    def __init__(self, r_half, age, magnitude, zero_point=27.0):
        self.r_half     = float(r_half)
        self.age        = float(age)
        self.magnitude  = float(magnitude)
        self.zero_point = float(zero_point)
        self.total_flux = mag_to_flux(magnitude, zero_point)

    def surface_brightness(self, r):
        raise NotImplementedError

    def generate_2d(self, shape):
        """
        Generate a 2D surface-brightness stamp.

        Parameters
        ----------
        shape : (ny, nx) tuple

        Returns
        -------
        image : ndarray  -- scaled to total_flux, NOT normalised
        """
        ny, nx   = shape
        cy, cx   = (ny - 1) / 2.0, (nx - 1) / 2.0
        y, x     = np.ogrid[:ny, :nx]
        r        = np.sqrt((x - cx)**2 + (y - cy)**2)
        sb       = self.surface_brightness(r).astype(np.float64)
        total    = sb.sum()
        if total > 0:
            sb *= self.total_flux / total
        return sb


# ---------------------------------------------------------------------------
# Profile implementations
# ---------------------------------------------------------------------------

class PlummerProfile(BaseProfile):
    """
    Plummer (1911) profile: I(r) ∝ (1 + (r/a)²)^(-2)

    r_half = a * sqrt(2^(1/2) - 1)  =>  a = r_half / sqrt(2^(1/2) - 1)
    """

    def __init__(self, r_half, age=1.0, magnitude=22.0, zero_point=27.0):
        super().__init__(r_half, age, magnitude, zero_point)
        self.a = r_half / np.sqrt(np.sqrt(2.0) - 1.0)

    def surface_brightness(self, r):
        return (1.0 + (r / self.a) ** 2) ** (-2.0)


class KingProfile(BaseProfile):
    """
    King (1962) profile: I(r) ∝ (1/sqrt(1+(r/rc)²) - 1/sqrt(1+(rt/rc)²))²

    concentration c = rt/rc  (tidal radius / core radius)
    r_half determined numerically from c.
    """

    def __init__(self, r_half, concentration=10.0, age=1.0,
                 magnitude=22.0, zero_point=27.0):
        super().__init__(r_half, age, magnitude, zero_point)
        self.concentration = float(concentration)
        self.rc, self.rt   = self._solve_radii()

    def _solve_radii(self):
        c  = self.concentration
        # rc from r_half: r_half ≈ rc * f(c)  (solved numerically)
        rt_over_rc = c
        # sample radii to find r_half numerically
        rc_guess = self.r_half / (0.5 * c)
        for _ in range(60):
            rc = rc_guess
            rt = c * rc
            r  = np.linspace(0, rt, 5000)
            sb = self._king_sb(r, rc, rt)
            cdf = np.cumsum(2 * np.pi * r * sb)
            if cdf[-1] > 0:
                cdf /= cdf[-1]
            idx = np.searchsorted(cdf, 0.5)
            r_half_est = r[min(idx, len(r)-1)]
            if abs(r_half_est - self.r_half) < 1e-4 * self.r_half:
                break
            rc_guess *= self.r_half / max(r_half_est, 1e-10)
        return rc_guess, c * rc_guess

    @staticmethod
    def _king_sb(r, rc, rt):
        term1 = 1.0 / np.sqrt(1.0 + (r  / rc) ** 2)
        term2 = 1.0 / np.sqrt(1.0 + (rt / rc) ** 2)
        sb    = np.where(r < rt, (term1 - term2) ** 2, 0.0)
        return sb

    def surface_brightness(self, r):
        return self._king_sb(r, self.rc, self.rt)


class EFFProfile(BaseProfile):
    """
    Elson, Fall & Freeman (1987) profile: I(r) ∝ (1 + (r/a)²)^(-γ/2)

    gamma > 2 for finite total luminosity.
    """

    def __init__(self, r_half, gamma=2.5, age=1.0,
                 magnitude=22.0, zero_point=27.0):
        super().__init__(r_half, age, magnitude, zero_point)
        self.gamma = max(float(gamma), 2.01)
        self.a     = self._solve_a()

    def _solve_a(self):
        # r_half: I(r_half) cumulative = 0.5 * total
        # Solved numerically
        g   = self.gamma
        a   = self.r_half  # initial guess
        for _ in range(60):
            r   = np.linspace(0, 20 * a, 10000)
            sb  = (1.0 + (r / a) ** 2) ** (-g / 2.0)
            cdf = np.cumsum(2 * np.pi * r * sb)
            if cdf[-1] > 0:
                cdf /= cdf[-1]
            idx       = np.searchsorted(cdf, 0.5)
            rh_est    = r[min(idx, len(r)-1)]
            if abs(rh_est - self.r_half) < 1e-4 * self.r_half:
                break
            a *= self.r_half / max(rh_est, 1e-10)
        return a

    def surface_brightness(self, r):
        return (1.0 + (r / self.a) ** 2) ** (-self.gamma / 2.0)


class SersicProfile(BaseProfile):
    """
    Sérsic (1963) profile: I(r) ∝ exp(-b_n * ((r/r_half)^(1/n) - 1))

    b_n ≈ 2n - 1/3 + 4/(405n) (Ciotti & Bertin 1999 approximation, n > 0.5)
    """

    def __init__(self, r_half, sersic_n=1.0, age=1.0,
                 magnitude=22.0, zero_point=27.0):
        super().__init__(r_half, age, magnitude, zero_point)
        self.sersic_n = max(float(sersic_n), 0.3)
        self.bn       = self._compute_bn()

    def _compute_bn(self):
        n = self.sersic_n
        return 2 * n - 1/3 + 4 / (405 * n)

    def surface_brightness(self, r):
        n  = self.sersic_n
        bn = self.bn
        rh = self.r_half
        return np.exp(-bn * ((r / rh) ** (1.0 / n) - 1.0))