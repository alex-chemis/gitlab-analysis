from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.patches as mpatches

def scatter_clusters(X, labels, out, title="", cluster_names=None):

    Path(out).parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, 8))
    scatter = plt.scatter(
        X[:, 0],
        X[:, 1],
        c=labels,
        s=1,
        alpha=0.7
    )
    plt.title(title)
    plt.xlabel("PC1") # the direction that explains the largest variance in language usage
    plt.ylabel("PC2") # the second most informative direction, orthogonal to PC1
    plt.colorbar(scatter, label="Cluster")

    if cluster_names:

        handles = [
            mpatches.Patch(
                color=scatter.cmap(scatter.norm(cid)),
                label=f"{cid} – {name}"
            )
            for cid, name in sorted(cluster_names.items())
        ]

        plt.legend(
            handles=handles,
            title="Cluster meaning",
            loc="best",
            fontsize=9
        )


    plt.tight_layout()
    plt.savefig(out, dpi=130)
    plt.close()

    