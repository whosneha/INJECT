import matplotlib.pyplot as plt
import numpy as np

def plot_injected_clusters(image, clusters, title="Injected Clusters"):
    plt.figure(figsize=(10, 10))
    plt.imshow(image, cmap='gray', origin='lower')
    for cluster in clusters:
        plt.scatter(cluster['x'], cluster['y'], s=cluster['size'], edgecolor='red', facecolor='none', label='Injected Cluster')
    plt.title(title)
    plt.xlabel("Pixel X")
    plt.ylabel("Pixel Y")
    plt.legend()
    plt.colorbar(label='Intensity')
    plt.show()

def plot_detection_results(detected_clusters, true_clusters, title="Detection Results"):
    plt.figure(figsize=(10, 10))
    plt.scatter(true_clusters[:, 0], true_clusters[:, 1], s=100, edgecolor='green', facecolor='none', label='True Clusters')
    plt.scatter(detected_clusters[:, 0], detected_clusters[:, 1], s=50, edgecolor='blue', facecolor='none', label='Detected Clusters')
    plt.title(title)
    plt.xlabel("Pixel X")
    plt.ylabel("Pixel Y")
    plt.legend()
    plt.grid()
    plt.show()

def plot_completeness(completeness_curve, title="Completeness Curve"):
    plt.figure(figsize=(8, 6))
    plt.plot(completeness_curve['magnitude'], completeness_curve['completeness'], marker='o')
    plt.title(title)
    plt.xlabel("Magnitude")
    plt.ylabel("Completeness")
    plt.grid()
    plt.ylim(0, 1)
    plt.xlim(np.min(completeness_curve['magnitude']), np.max(completeness_curve['magnitude']))
    plt.axhline(0.5, color='red', linestyle='--', label='50% Completeness')
    plt.legend()
    plt.show()