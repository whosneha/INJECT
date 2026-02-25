"""
Cluster model generation module.

Supports two approaches:
1. Smooth Profile: Treat cluster as a smooth extended source (fast, good for distant clusters)
2. Discrete Stars: Generate individual stars with positions and magnitudes (realistic, resolved clusters)
"""

import numpy as np
from .light_profiles import PlummerProfile, KingProfile, EFFProfile, SersicProfile, mag_to_flux


# =============================================================================
# LUMINOSITY FUNCTIONS
# =============================================================================

def kroupa_imf(n_stars, m_min=0.1, m_max=100.0, seed=None):
    """
    Generate stellar masses from Kroupa (2001) Initial Mass Function.
    
    IMF: dN/dM ~ M^(-alpha)
    alpha = 0.3 for M < 0.08
    alpha = 1.3 for 0.08 <= M < 0.5
    alpha = 2.3 for M >= 0.5
    
    Parameters:
    -----------
    n_stars : int
        Number of stars to generate
    m_min : float
        Minimum stellar mass in solar masses
    m_max : float
        Maximum stellar mass in solar masses
    seed : int, optional
        Random seed
    
    Returns:
    --------
    masses : ndarray
        Stellar masses in solar masses
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Use inverse transform sampling with piecewise power law
    masses = []
    
    while len(masses) < n_stars:
        # Generate from broken power law using rejection sampling
        m = np.random.uniform(m_min, m_max)
        
        if m < 0.08:
            alpha = 0.3
            norm = 1.0
        elif m < 0.5:
            alpha = 1.3
            norm = 0.08 ** (1.3 - 0.3)
        else:
            alpha = 2.3
            norm = 0.08 ** (1.3 - 0.3) * 0.5 ** (2.3 - 1.3)
        
        # Probability proportional to M^(-alpha)
        p = norm * m ** (-alpha)
        p_max = m_min ** (-0.3)  # Maximum probability at m_min
        
        if np.random.uniform(0, p_max) < p:
            masses.append(m)
    
    return np.array(masses[:n_stars])


def chabrier_imf(n_stars, m_min=0.1, m_max=100.0, seed=None):
    """
    Generate stellar masses from Chabrier (2003) IMF.
    
    Log-normal for M < 1 Msun, power law for M >= 1 Msun
    
    Parameters:
    -----------
    n_stars : int
        Number of stars to generate
    m_min : float
        Minimum stellar mass
    m_max : float
        Maximum stellar mass
    seed : int, optional
        Random seed
    
    Returns:
    --------
    masses : ndarray
        Stellar masses in solar masses
    """
    if seed is not None:
        np.random.seed(seed)
    
    masses = []
    
    while len(masses) < n_stars:
        m = np.random.uniform(m_min, m_max)
        
        if m < 1.0:
            # Log-normal
            mc = 0.08  # Characteristic mass
            sigma = 0.69
            p = np.exp(-(np.log10(m) - np.log10(mc))**2 / (2 * sigma**2)) / m
        else:
            # Power law with alpha = 2.3
            p = m ** (-2.3)
        
        p_max = 1.0 / m_min
        
        if np.random.uniform(0, p_max) < p:
            masses.append(m)
    
    return np.array(masses[:n_stars])


def salpeter_imf(n_stars, m_min=0.1, m_max=100.0, seed=None):
    """
    Generate stellar masses from Salpeter (1955) IMF.
    
    dN/dM ~ M^(-2.35)
    
    Parameters:
    -----------
    n_stars : int
        Number of stars
    m_min : float
        Minimum mass
    m_max : float
        Maximum mass
    seed : int, optional
        Random seed
    
    Returns:
    --------
    masses : ndarray
        Stellar masses
    """
    if seed is not None:
        np.random.seed(seed)
    
    alpha = 2.35
    
    # Inverse transform sampling for power law
    u = np.random.uniform(0, 1, n_stars)
    
    # CDF^(-1) for power law
    masses = ((m_max**(1-alpha) - m_min**(1-alpha)) * u + m_min**(1-alpha))**(1/(1-alpha))
    
    return masses


def mass_to_luminosity(mass, age_gyr=1.0, metallicity=0.02):
    """
    Convert stellar mass to luminosity using simple scaling relations.
    
    For main sequence stars: L ~ M^3.5 (approximate)
    
    Parameters:
    -----------
    mass : float or ndarray
        Stellar mass in solar masses
    age_gyr : float
        Cluster age in Gyr (affects evolved stars)
    metallicity : float
        Metallicity Z (solar = 0.02)
    
    Returns:
    --------
    luminosity : float or ndarray
        Luminosity in solar luminosities
    """
    mass = np.asarray(mass)
    
    # Simple mass-luminosity relation
    # Low mass: L ~ M^2.3
    # High mass: L ~ M^3.5
    luminosity = np.where(mass < 0.5, mass**2.3, mass**3.5)
    
    # Age correction (rough approximation for evolved stars)
    if age_gyr > 1.0:
        # Massive stars evolve faster
        turnoff_mass = 10.0 / age_gyr**0.4  # Approximate main sequence turnoff
        evolved = mass > turnoff_mass
        luminosity[evolved] *= 10.0  # Giants are brighter
    
    return luminosity


def luminosity_to_magnitude(luminosity, distance_pc=10.0, band='V'):
    """
    Convert luminosity to apparent magnitude.
    
    Parameters:
    -----------
    luminosity : float or ndarray
        Luminosity in solar luminosities
    distance_pc : float
        Distance in parsecs
    band : str
        Photometric band (currently only 'V' implemented properly)
    
    Returns:
    --------
    magnitude : float or ndarray
        Apparent magnitude
    """
    # Absolute magnitude of Sun in V band
    M_sun_V = 4.83
    
    # Absolute magnitude
    M = M_sun_V - 2.5 * np.log10(luminosity)
    
    # Distance modulus
    dm = 5 * np.log10(distance_pc / 10.0)
    
    return M + dm


# =============================================================================
# SPATIAL DISTRIBUTIONS
# =============================================================================

def plummer_positions(n_stars, r_half, seed=None):
    """
    Generate star positions following a Plummer distribution.
    
    Parameters:
    -----------
    n_stars : int
        Number of stars
    r_half : float
        Half-light radius in pixels
    seed : int, optional
        Random seed
    
    Returns:
    --------
    r : ndarray
        Radial distances
    theta : ndarray
        Angular positions (0 to 2*pi)
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Plummer scale radius
    a = r_half / np.sqrt(np.sqrt(2) - 1)
    
    # Inverse transform sampling for Plummer
    # CDF: M(r) = r^3 / (r^2 + a^2)^(3/2)
    u = np.random.uniform(0, 1, n_stars)
    
    # Solve for r: u = r^3 / (r^2 + a^2)^(3/2)
    # r = a * (u^(-2/3) - 1)^(-1/2)
    r = a / np.sqrt(u**(-2/3) - 1)
    
    # Random angles
    theta = np.random.uniform(0, 2*np.pi, n_stars)
    
    return r, theta


def king_positions(n_stars, r_c, r_t, seed=None):
    """
    Generate star positions following a King distribution.
    
    Parameters:
    -----------
    n_stars : int
        Number of stars
    r_c : float
        Core radius in pixels
    r_t : float
        Tidal radius in pixels
    seed : int, optional
        Random seed
    
    Returns:
    --------
    r : ndarray
        Radial distances
    theta : ndarray
        Angular positions
    """
    if seed is not None:
        np.random.seed(seed)
    
    # Use rejection sampling for King profile
    c = r_t / r_c
    
    r = []
    while len(r) < n_stars:
        # Propose from uniform in [0, r_t]
        r_prop = np.random.uniform(0, r_t)
        
        # King profile probability
        term1 = 1.0 / np.sqrt(1 + (r_prop / r_c)**2)
        term2 = 1.0 / np.sqrt(1 + c**2)
        p = (term1 - term2)**2 if r_prop < r_t else 0
        
        # Maximum probability at r=0
        p_max = (1 - term2)**2
        
        if np.random.uniform(0, p_max) < p:
            r.append(r_prop)
    
    r = np.array(r[:n_stars])
    theta = np.random.uniform(0, 2*np.pi, n_stars)
    
    return r, theta


def eff_positions(n_stars, a, gamma, seed=None):
    """
    Generate star positions following an EFF distribution.
    
    Parameters:
    -----------
    n_stars : int
        Number of stars
    a : float
        Scale radius in pixels
    gamma : float
        Power law index
    seed : int, optional
        Random seed
    
    Returns:
    --------
    r : ndarray
        Radial distances
    theta : ndarray
        Angular positions
    """
    if seed is not None:
        np.random.seed(seed)
    
    # EFF profile: I(r) ~ (1 + r^2/a^2)^(-gamma/2)
    # Use rejection sampling
    r_max = 10 * a  # Truncate at some radius
    
    r = []
    while len(r) < n_stars:
        r_prop = np.random.uniform(0, r_max)
        p = (1 + (r_prop / a)**2)**(-gamma/2)
        p_max = 1.0
        
        if np.random.uniform(0, p_max) < p:
            r.append(r_prop)
    
    r = np.array(r[:n_stars])
    theta = np.random.uniform(0, 2*np.pi, n_stars)
    
    return r, theta


# =============================================================================
# DISCRETE STAR CLUSTER CLASS
# =============================================================================

class DiscreteStarCluster:
    """
    Generate a star cluster as a collection of discrete stars.
    
    Each star has a position, mass, luminosity, and magnitude.
    """
    
    def __init__(self, n_stars, r_half, total_magnitude=None, total_flux=None,
                 profile_type='plummer', imf='kroupa', age_gyr=1.0,
                 concentration=30, gamma=2.5, distance_pc=10000,
                 seed=None):
        """
        Initialize a discrete star cluster.
        
        Parameters:
        -----------
        n_stars : int
            Number of stars to generate
        r_half : float
            Half-light radius in pixels
        total_magnitude : float, optional
            Total integrated magnitude of cluster
        total_flux : float, optional
            Total integrated flux (alternative to magnitude)
        profile_type : str
            Spatial distribution: 'plummer', 'king', 'eff'
        imf : str
            Initial mass function: 'kroupa', 'chabrier', 'salpeter'
        age_gyr : float
            Cluster age in Gyr
        concentration : float
            Concentration parameter for King profile (c = r_t / r_c)
        gamma : float
            Power law index for EFF profile
        distance_pc : float
            Distance in parsecs (for magnitude calculation)
        seed : int, optional
            Random seed for reproducibility
        """
        self.n_stars = n_stars
        self.r_half = r_half
        self.profile_type = profile_type
        self.imf_type = imf
        self.age_gyr = age_gyr
        self.concentration = concentration
        self.gamma = gamma
        self.distance_pc = distance_pc
        self.seed = seed
        
        # Generate stars
        self._generate_stars()
        
        # Scale to total magnitude/flux
        if total_magnitude is not None:
            self.scale_to_magnitude(total_magnitude)
        elif total_flux is not None:
            self.scale_to_flux(total_flux)
    
    def _generate_stars(self):
        """Generate star positions, masses, and luminosities."""
        # Generate masses from IMF
        if self.imf_type == 'kroupa':
            self.masses = kroupa_imf(self.n_stars, seed=self.seed)
        elif self.imf_type == 'chabrier':
            self.masses = chabrier_imf(self.n_stars, seed=self.seed)
        elif self.imf_type == 'salpeter':
            self.masses = salpeter_imf(self.n_stars, seed=self.seed)
        else:
            raise ValueError(f"Unknown IMF: {self.imf_type}")
        
        # Generate positions
        if self.profile_type == 'plummer':
            self.radii, self.angles = plummer_positions(
                self.n_stars, self.r_half, seed=self.seed
            )
        elif self.profile_type == 'king':
            # Convert r_half to r_c for King profile
            r_c = self.r_half / (np.sqrt(self.concentration) * 0.5)
            r_t = r_c * self.concentration
            self.radii, self.angles = king_positions(
                self.n_stars, r_c, r_t, seed=self.seed
            )
        elif self.profile_type == 'eff':
            # Convert r_half to scale radius for EFF
            a = self.r_half / np.sqrt(2**(2/(self.gamma - 2)) - 1)
            self.radii, self.angles = eff_positions(
                self.n_stars, a, self.gamma, seed=self.seed
            )
        else:
            raise ValueError(f"Unknown profile type: {self.profile_type}")
        
        # Convert to Cartesian (relative to center)
        self.x_offset = self.radii * np.cos(self.angles)
        self.y_offset = self.radii * np.sin(self.angles)
        
        # Calculate luminosities
        self.luminosities = mass_to_luminosity(self.masses, self.age_gyr)
        
        # Calculate magnitudes
        self.magnitudes = luminosity_to_magnitude(
            self.luminosities, self.distance_pc
        )
        
        # Calculate fluxes
        self.fluxes = 10**((27.0 - self.magnitudes) / 2.5)  # Arbitrary zero point
    
    def scale_to_magnitude(self, total_magnitude):
        """Scale all star fluxes to achieve a target total magnitude."""
        target_flux = mag_to_flux(total_magnitude)
        current_flux = np.sum(self.fluxes)
        scale_factor = target_flux / current_flux
        
        self.fluxes *= scale_factor
        self.magnitudes = 27.0 - 2.5 * np.log10(self.fluxes)
        
        self.total_flux = target_flux
        self.total_magnitude = total_magnitude
    
    def scale_to_flux(self, total_flux):
        """Scale all star fluxes to achieve a target total flux."""
        current_flux = np.sum(self.fluxes)
        scale_factor = total_flux / current_flux
        
        self.fluxes *= scale_factor
        self.magnitudes = 27.0 - 2.5 * np.log10(self.fluxes)
        
        self.total_flux = total_flux
        self.total_magnitude = 27.0 - 2.5 * np.log10(total_flux)
    
    def generate_2d(self, shape, center=None):
        """
        Generate a 2D image of the cluster with stars as delta functions.
        
        Parameters:
        -----------
        shape : tuple
            Output image shape (ny, nx)
        center : tuple, optional
            Center position (y, x). Defaults to image center.
        
        Returns:
        --------
        image : ndarray
            2D image with stars placed as point sources
        """
        ny, nx = shape
        if center is None:
            center = (ny // 2, nx // 2)
        
        image = np.zeros(shape, dtype=float)
        
        # Place each star
        for x_off, y_off, flux in zip(self.x_offset, self.y_offset, self.fluxes):
            x = int(round(center[1] + x_off))
            y = int(round(center[0] + y_off))
            
            if 0 <= x < nx and 0 <= y < ny:
                image[y, x] += flux
        
        return image
    
    def get_star_catalog(self, center=(0, 0)):
        """
        Get a catalog of all stars with positions and properties.
        
        Parameters:
        -----------
        center : tuple
            Center position (y, x) to add to offsets
        
        Returns:
        --------
        catalog : list of dict
            Star catalog with positions, magnitudes, fluxes, masses
        """
        catalog = []
        for i in range(self.n_stars):
            catalog.append({
                'id': i,
                'x': center[1] + self.x_offset[i],
                'y': center[0] + self.y_offset[i],
                'radius': self.radii[i],
                'magnitude': self.magnitudes[i],
                'flux': self.fluxes[i],
                'mass': self.masses[i],
                'luminosity': self.luminosities[i]
            })
        return catalog
    
    def get_properties(self):
        """Get summary properties of the cluster."""
        return {
            'n_stars': self.n_stars,
            'r_half': self.r_half,
            'profile_type': self.profile_type,
            'imf': self.imf_type,
            'age_gyr': self.age_gyr,
            'total_magnitude': getattr(self, 'total_magnitude', None),
            'total_flux': getattr(self, 'total_flux', np.sum(self.fluxes)),
            'mass_range': (self.masses.min(), self.masses.max()),
            'mag_range': (self.magnitudes.min(), self.magnitudes.max()),
        }


# =============================================================================
# UNIFIED CLUSTER FACTORY
# =============================================================================

def create_cluster(method='smooth', **kwargs):
    """
    Factory function to create a cluster model.
    
    Parameters:
    -----------
    method : str
        'smooth' for extended source profile, 'discrete' for individual stars
    
    For method='smooth':
        r_half : float
            Half-light radius in pixels
        profile_type : str
            'plummer', 'king', 'eff', 'sersic'
        magnitude : float, optional
            Total magnitude
        central_brightness : float, optional
            Central surface brightness (if magnitude not given)
        age : float
            Age in Gyr
        concentration : float
            For King profile
        gamma : float
            For EFF profile
        sersic_n : float
            For Sersic profile
    
    For method='discrete':
        n_stars : int
            Number of stars
        r_half : float
            Half-light radius
        total_magnitude : float, optional
            Total magnitude
        profile_type : str
            'plummer', 'king', 'eff'
        imf : str
            'kroupa', 'chabrier', 'salpeter'
        age_gyr : float
            Age in Gyr
        seed : int, optional
            Random seed
    
    Returns:
    --------
    cluster : object
        Cluster model (PlummerProfile/KingProfile/etc. or DiscreteStarCluster)
    """
    if method == 'smooth':
        profile_type = kwargs.get('profile_type', 'plummer')
        r_half = kwargs['r_half']
        age = kwargs.get('age', 1.0)
        magnitude = kwargs.get('magnitude')
        central_brightness = kwargs.get('central_brightness', 1.0)
        
        if profile_type == 'plummer':
            return PlummerProfile(
                r_half=r_half, age=age,
                magnitude=magnitude, central_brightness=central_brightness
            )
        elif profile_type == 'king':
            return KingProfile(
                r_half=r_half,
                concentration=kwargs.get('concentration', 30),
                age=age,
                magnitude=magnitude, central_brightness=central_brightness
            )
        elif profile_type == 'eff':
            return EFFProfile(
                r_half=r_half,
                gamma=kwargs.get('gamma', 2.5),
                age=age,
                magnitude=magnitude, central_brightness=central_brightness
            )
        elif profile_type == 'sersic':
            return SersicProfile(
                r_half=r_half,
                sersic_n=kwargs.get('sersic_n', 2.0),
                age=age,
                magnitude=magnitude, central_brightness=central_brightness
            )
        else:
            raise ValueError(f"Unknown profile type: {profile_type}")
    
    elif method == 'discrete':
        return DiscreteStarCluster(
            n_stars=kwargs['n_stars'],
            r_half=kwargs['r_half'],
            total_magnitude=kwargs.get('total_magnitude'),
            total_flux=kwargs.get('total_flux'),
            profile_type=kwargs.get('profile_type', 'plummer'),
            imf=kwargs.get('imf', 'kroupa'),
            age_gyr=kwargs.get('age_gyr', 1.0),
            concentration=kwargs.get('concentration', 30),
            gamma=kwargs.get('gamma', 2.5),
            distance_pc=kwargs.get('distance_pc', 10000),
            seed=kwargs.get('seed')
        )
    
    else:
        raise ValueError(f"Unknown method: {method}. Use 'smooth' or 'discrete'.")
