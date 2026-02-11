import numpy as np

def mag_to_flux(mag, zero_point=27.0):
    """Convert magnitude to flux. Default zero-point for typical surveys."""
    return 10 ** ((zero_point - mag) / 2.5)

def flux_to_mag(flux, zero_point=27.0):
    """Convert flux to magnitude."""
    return zero_point - 2.5 * np.log10(flux)


class KingProfile:
    """
    King (1962) profile for globular clusters.
    Models tidally truncated stellar systems.
    """
    def __init__(self, r_half, concentration, age, magnitude=None, central_brightness=1.0, zero_point=27.0):
        """
        Parameters:
        -----------
        r_half : float
            Half-light radius in pixels or arcsec
        concentration : float
            c = r_t / r_c (typically 5-30 for open clusters, 30-300 for globulars)
        age : float
            Age in Gyr
        magnitude : float, optional
            Total integrated magnitude. If provided, overrides central_brightness.
        central_brightness : float
            Central surface brightness (used if magnitude is None)
        zero_point : float
            Photometric zero point for magnitude conversion
        """
        self.concentration = concentration
        self.age = age
        self.zero_point = zero_point
        
        # For King profile: r_half ≈ r_c * sqrt(concentration) for large c
        # More accurate: solve numerically, but this is a good approximation
        self.r_half = r_half
        self.r_c = r_half / self._r_half_to_r_c_ratio()
        self.r_t = self.r_c * concentration
        self.size = self.r_c  # alias
        
        if magnitude is not None:
            self.magnitude = magnitude
            self.total_flux = mag_to_flux(magnitude, zero_point)
            # Compute central brightness from total flux
            self.central_brightness = self._flux_to_central_brightness(self.total_flux)
        else:
            self.central_brightness = central_brightness
            self.total_flux = self._compute_total_flux()
            self.magnitude = flux_to_mag(self.total_flux, zero_point)

    def _r_half_to_r_c_ratio(self):
        """Approximate ratio of half-light radius to core radius for King profile."""
        c = self.concentration
        # Empirical approximation that works well for c > 5
        return np.sqrt(c) * 0.5 if c > 5 else 1.0

    def _compute_total_flux(self):
        """Compute total integrated flux numerically."""
        r = np.linspace(0, self.r_t, 1000)
        brightness = self.compute_brightness(r)
        # Integrate 2*pi*r*I(r) dr
        return 2 * np.pi * np.trapz(brightness * r, r)

    def _flux_to_central_brightness(self, total_flux):
        """Compute central brightness needed to achieve given total flux."""
        # First compute flux with central_brightness = 1
        self.central_brightness = 1.0
        flux_normalized = self._compute_total_flux()
        return total_flux / flux_normalized

    def compute_brightness(self, radius):
        """
        Compute King profile surface brightness at given radius.
        I(r) = I_0 * [ 1/sqrt(1 + (r/r_c)^2) - 1/sqrt(1 + (r_t/r_c)^2) ]^2
        """
        r = np.asarray(radius, dtype=float)
        
        term1 = 1.0 / np.sqrt(1 + (r / self.r_c) ** 2)
        term2 = 1.0 / np.sqrt(1 + self.concentration ** 2)
        
        # Normalization factor so I(0) = central_brightness
        norm = (1.0 - term2) ** 2
        
        brightness = self.central_brightness * ((term1 - term2) ** 2) / norm
        
        # Set brightness to zero beyond tidal radius
        brightness = np.where(r >= self.r_t, 0.0, brightness)
        
        if np.isscalar(radius):
            return float(brightness)
        return brightness

    def generate_2d(self, shape, center=None):
        """Generate a 2D image of the profile."""
        ny, nx = shape
        if center is None:
            center = (ny // 2, nx // 2)
        y, x = np.ogrid[:ny, :nx]
        r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
        return self.compute_brightness(r)

    def get_properties(self):
        return {
            'r_half': self.r_half,
            'r_c': self.r_c,
            'r_t': self.r_t,
            'concentration': self.concentration,
            'age': self.age,
            'magnitude': self.magnitude,
            'total_flux': self.total_flux,
            'central_brightness': self.central_brightness
        }


class EFFProfile:
    """
    Elson, Fall & Freeman (1987) profile for young star clusters.
    Power-law profile commonly used for LMC/SMC clusters.
    """
    def __init__(self, r_half, gamma, age, magnitude=None, central_brightness=1.0, zero_point=27.0):
        """
        Parameters:
        -----------
        r_half : float
            Half-light radius in pixels or arcsec
        gamma : float
            Power-law index (typically 2.2-3.5 for young clusters)
        age : float
            Age in Gyr
        magnitude : float, optional
            Total integrated magnitude. If provided, overrides central_brightness.
        """
        self.gamma = gamma
        self.concentration = gamma  # alias
        self.age = age
        self.zero_point = zero_point
        self.r_half = r_half
        
        # Convert half-light radius to scale radius
        # For EFF: r_half = a * sqrt(2^(2/(gamma-2)) - 1)
        if gamma > 2:
            self.size = r_half / np.sqrt(2**(2/(gamma - 2)) - 1)
        else:
            self.size = r_half  # fallback
        
        if magnitude is not None:
            self.magnitude = magnitude
            self.total_flux = mag_to_flux(magnitude, zero_point)
            self.central_brightness = self._flux_to_central_brightness(self.total_flux)
        else:
            self.central_brightness = central_brightness
            self.total_flux = self._compute_total_flux()
            self.magnitude = flux_to_mag(self.total_flux, zero_point)

    def _compute_total_flux(self, r_max=1000):
        """Compute total integrated flux numerically."""
        r = np.linspace(0, r_max, 5000)
        brightness = self.compute_brightness(r)
        return 2 * np.pi * np.trapz(brightness * r, r)

    def _flux_to_central_brightness(self, total_flux):
        """Compute central brightness needed to achieve given total flux."""
        self.central_brightness = 1.0
        flux_normalized = self._compute_total_flux()
        return total_flux / flux_normalized

    def compute_brightness(self, radius):
        """
        Compute EFF profile surface brightness.
        I(r) = I_0 * (1 + r^2/a^2)^(-gamma/2)
        """
        r = np.asarray(radius, dtype=float)
        a = self.size
        
        brightness = self.central_brightness * (1 + (r / a) ** 2) ** (-self.gamma / 2)
        
        if np.isscalar(radius):
            return float(brightness)
        return brightness

    def half_light_radius(self):
        """Return the half-light radius."""
        return self.r_half

    def generate_2d(self, shape, center=None):
        """Generate a 2D image of the profile."""
        ny, nx = shape
        if center is None:
            center = (ny // 2, nx // 2)
        y, x = np.ogrid[:ny, :nx]
        r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
        return self.compute_brightness(r)

    def get_properties(self):
        return {
            'r_half': self.r_half,
            'size': self.size,
            'gamma': self.gamma,
            'age': self.age,
            'magnitude': self.magnitude,
            'total_flux': self.total_flux,
            'central_brightness': self.central_brightness
        }


class PlummerProfile:
    """
    Plummer (1911) profile - simple analytical model for star clusters.
    Good approximation for many globular clusters.
    """
    def __init__(self, r_half, age, magnitude=None, central_brightness=1.0, zero_point=27.0):
        """
        Parameters:
        -----------
        r_half : float
            Half-light radius in pixels or arcsec
        age : float
            Age in Gyr
        magnitude : float, optional
            Total integrated magnitude. If provided, overrides central_brightness.
        """
        self.age = age
        self.zero_point = zero_point
        self.r_half = r_half
        self.concentration = None
        
        # For Plummer: r_half = a * sqrt(sqrt(2) - 1) ≈ 0.64 * a
        self.size = r_half / np.sqrt(np.sqrt(2) - 1)
        
        if magnitude is not None:
            self.magnitude = magnitude
            self.total_flux = mag_to_flux(magnitude, zero_point)
            self.central_brightness = self._flux_to_central_brightness(self.total_flux)
        else:
            self.central_brightness = central_brightness
            self.total_flux = self._compute_total_flux()
            self.magnitude = flux_to_mag(self.total_flux, zero_point)

    def _compute_total_flux(self):
        """Compute total integrated flux analytically for Plummer."""
        # For Plummer: total flux = pi * a^2 * I_0
        return np.pi * self.size**2 * self.central_brightness

    def _flux_to_central_brightness(self, total_flux):
        """Compute central brightness needed to achieve given total flux."""
        return total_flux / (np.pi * self.size**2)

    def compute_brightness(self, radius):
        """
        Compute Plummer profile surface brightness.
        I(r) = I_0 * (1 + r^2/a^2)^(-2)
        """
        r = np.asarray(radius, dtype=float)
        a = self.size
        
        brightness = self.central_brightness * (1 + (r / a) ** 2) ** (-2)
        
        if np.isscalar(radius):
            return float(brightness)
        return brightness

    def half_light_radius(self):
        """Return the half-light radius."""
        return self.r_half

    def generate_2d(self, shape, center=None):
        """Generate a 2D image of the profile."""
        ny, nx = shape
        if center is None:
            center = (ny // 2, nx // 2)
        y, x = np.ogrid[:ny, :nx]
        r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
        return self.compute_brightness(r)

    def get_properties(self):
        return {
            'r_half': self.r_half,
            'size': self.size,
            'age': self.age,
            'magnitude': self.magnitude,
            'total_flux': self.total_flux,
            'central_brightness': self.central_brightness
        }


class SersicProfile:
    """
    Sersic profile - generalized model that includes exponential (n=1) 
    and de Vaucouleurs (n=4) as special cases.
    """
    def __init__(self, r_half, sersic_n, age, magnitude=None, central_brightness=1.0, zero_point=27.0):
        """
        Parameters:
        -----------
        r_half : float
            Half-light (effective) radius in pixels or arcsec
        sersic_n : float
            Sersic index (0.5-1 for disks, 4 for ellipticals)
        age : float
            Age in Gyr
        magnitude : float, optional
            Total integrated magnitude. If provided, overrides central_brightness.
        """
        self.sersic_n = sersic_n
        self.concentration = sersic_n  # alias
        self.age = age
        self.zero_point = zero_point
        self.r_half = r_half
        self.size = r_half  # effective radius
        
        # Approximation for b_n
        self.b_n = 2 * sersic_n - 1/3 + 4/(405*sersic_n)
        
        if magnitude is not None:
            self.magnitude = magnitude
            self.total_flux = mag_to_flux(magnitude, zero_point)
            self.central_brightness = self._flux_to_central_brightness(self.total_flux)
        else:
            self.central_brightness = central_brightness
            self.total_flux = self._compute_total_flux()
            self.magnitude = flux_to_mag(self.total_flux, zero_point)

    def _compute_total_flux(self, r_max=500):
        """Compute total integrated flux numerically."""
        r = np.linspace(0, r_max, 5000)
        brightness = self.compute_brightness(r)
        return 2 * np.pi * np.trapz(brightness * r, r)

    def _flux_to_central_brightness(self, total_flux):
        """Compute central brightness needed to achieve given total flux."""
        self.central_brightness = 1.0
        flux_normalized = self._compute_total_flux()
        return total_flux / flux_normalized

    def compute_brightness(self, radius):
        """
        Compute Sersic profile surface brightness.
        I(r) = I_e * exp(-b_n * [(r/r_e)^(1/n) - 1])
        """
        r = np.asarray(radius, dtype=float)
        r_e = self.size
        n = self.sersic_n
        
        # Avoid division by zero at r=0
        with np.errstate(divide='ignore', invalid='ignore'):
            brightness = self.central_brightness * np.exp(
                -self.b_n * ((r / r_e) ** (1/n) - 1)
            )
        
        if np.isscalar(radius):
            return float(brightness)
        return brightness

    def half_light_radius(self):
        """Return the half-light radius."""
        return self.r_half

    def generate_2d(self, shape, center=None):
        """Generate a 2D image of the profile."""
        ny, nx = shape
        if center is None:
            center = (ny // 2, nx // 2)
        y, x = np.ogrid[:ny, :nx]
        r = np.sqrt((x - center[1])**2 + (y - center[0])**2)
        return self.compute_brightness(r)

    def get_properties(self):
        return {
            'r_half': self.r_half,
            'size': self.size,
            'sersic_n': self.sersic_n,
            'age': self.age,
            'magnitude': self.magnitude,
            'total_flux': self.total_flux,
            'central_brightness': self.central_brightness
        }