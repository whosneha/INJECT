def inject_cluster(image, cluster_profile, position, noise_level=0.0):
    """
    Injects a cluster into the given image at the specified position.

    Parameters:
    - image: The image into which the cluster will be injected.
    - cluster_profile: The profile of the cluster to inject (e.g., KingProfile).
    - position: A tuple (x, y) indicating the position to inject the cluster.
    - noise_level: The level of noise to add to the image after injection.

    Returns:
    - The modified image with the injected cluster.
    """
    # Create a copy of the image to avoid modifying the original
    modified_image = image.copy()

    # Generate the cluster profile at the specified position
    cluster_image = cluster_profile.generate_image()

    # Inject the cluster into the image
    x, y = position
    modified_image[y:y + cluster_image.shape[0], x:x + cluster_image.shape[1]] += cluster_image

    # Add noise if specified
    if noise_level > 0:
        noise = np.random.normal(0, noise_level, modified_image.shape)
        modified_image += noise

    return modified_image


def prepare_injection(image, cluster_profiles, positions, noise_level=0.0):
    """
    Prepares an image for injection of multiple clusters.

    Parameters:
    - image: The image into which clusters will be injected.
    - cluster_profiles: A list of cluster profiles to inject.
    - positions: A list of tuples indicating positions for each cluster.
    - noise_level: The level of noise to add to the image after injection.

    Returns:
    - The modified image with all injected clusters.
    """
    modified_image = image.copy()

    for cluster_profile, position in zip(cluster_profiles, positions):
        modified_image = inject_cluster(modified_image, cluster_profile, position, noise_level)

    return modified_image