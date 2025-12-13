"""
ML-кластеризация проектов GitLab по использованным языкам
(батчево, без сохранения в Mongo)
"""

import argparse
import numpy as np
from sklearn.feature_extraction import DictVectorizer
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import IncrementalPCA

from scripts.common.mongo import iter_projects
from scripts.common.batch import batched
from scripts.common.plot_scatter import scatter_clusters

BATCH = 1000
RANDOM_STATE = 42
LOG_THRESHOLD=500000

LANG_GROUPS = {
    "systems": {"C", "C++", "Rust"},
    "jvm": {"Java", "Kotlin", "Scala"},
    "mobile": {"Kotlin"},
    "frontend": {"JavaScript", "TypeScript", "HTML", "CSS"},
    "backend": {"Go", "Java", "C#", "PHP"},
    "ml": {"Python", "Jupyter Notebook"},
    "infra": {"Dockerfile", "Shell", "Makefile", "CMake"},
}

def top_languages(center, feature_names, k=6):
    idx = np.argsort(center)[-k:][::-1]
    return [feature_names[i] for i in idx]


def compute_group_weights(center, feature_names):
    weights = {g: 0.0 for g in LANG_GROUPS}
    total = center.sum() or 1.0

    for value, lang in zip(center, feature_names):
        for group, langs in LANG_GROUPS.items():
            if lang in langs:
                weights[group] += value

    for g in weights:
        weights[g] /= total

    return weights


def name_cluster(center, feature_names):
    top_langs = top_languages(center, feature_names)
    gw = compute_group_weights(center, feature_names)

    if gw["ml"] > 0.45 and "Jupyter Notebook" in top_langs:
        return "Data Science / ML"

    if gw["mobile"] > 0.3 and gw["jvm"] > 0.3:
        return "Mobile Development (Android / JVM)"

    if gw["systems"] > 0.45 and gw["infra"] < 0.3:
        return "Low-Level / Systems Programming"
    
    if gw["systems"] > 0.25 and gw["infra"] > 0.35:
        return "Embedded / Systems Tooling"

    if gw["jvm"] > 0.45 and gw["frontend"] < 0.4:
        return "JVM Backend / Enterprise"

    if gw["backend"] > 0.3 and gw["infra"] > 0.35:
        return "Cloud / Backend – DevOps-heavy"

    if gw["frontend"] > 0.5 and gw["backend"] < 0.25:
        return "Web Frontend – UI-centric"

    if gw["backend"] > gw["frontend"] and gw["backend"] > 0.25:
        return "Polyglot Backend Services"

    if gw["infra"] > 0.45:
        return "Infrastructure / Automation"

    if gw["frontend"] > 0.25 and gw["backend"] > 0.25:
        return "Web / Enterprise Applications"

    return "Miscellaneous / Experimental"


def main():
    ap = argparse.ArgumentParser(
        description="ML clustering of projects by languages (RAM-safe)"
    )
    ap.add_argument("--clusters", type=int, default=6, help="Number of clusters")
    ap.add_argument("--max-projects", type=int, default=50000, help="Limit projects")
    ap.add_argument("--out", type=str, required=True, help="PNG output")
    args = ap.parse_args()

    # === MODELS ===
    vec = DictVectorizer(sparse=True)
    kmeans = MiniBatchKMeans(
        n_clusters=args.clusters,
        batch_size=BATCH,
        random_state=RANDOM_STATE
    )
    ipca = IncrementalPCA(n_components=2, batch_size=BATCH)

    # === 1. TRAIN KMEANS (PARTIAL FIT) ===
    fitted_vec = False
    seen = 0

    print("[1/3] Training MiniBatchKMeans...")
    next_log = LOG_THRESHOLD

    for batch in batched(iter_projects({"languages": 1}), BATCH):
        batch = [p for p in batch if p.get("languages")]
        if not batch:
            continue

        X = (
            vec.fit_transform(p["languages"] for p in batch)
            if not fitted_vec
            else vec.transform(p["languages"] for p in batch)
        )

        kmeans.partial_fit(X)
        fitted_vec = True

        seen += len(batch)

        if seen >= next_log:
            print(f"  trained on {seen} projects")
            next_log += LOG_THRESHOLD

    # === 2. FIT PCA ===
    print("[2/3] Fitting Incremental PCA...")

    seen = 0
    next_log = LOG_THRESHOLD
    for batch in batched(iter_projects({"languages": 1}), BATCH):
        batch = [p for p in batch if p.get("languages")]
        if not batch:
            continue

        X = vec.transform(p["languages"] for p in batch).toarray()
        ipca.partial_fit(X)

        seen += len(batch)
        if seen >= args.max_projects:
            break
        if seen >= next_log:
            print(f"  fit {seen} projects")
            next_log += LOG_THRESHOLD

    # === 3. TRANSFORM + PLOT ===
    print("[3/3] Projecting and plotting...")

    X_all = []
    y_all = []
    seen = 0
    next_log = LOG_THRESHOLD

    for batch in batched(iter_projects({"languages": 1}), BATCH):
        batch = [p for p in batch if p.get("languages")]
        if not batch:
            continue

        X = vec.transform(p["languages"] for p in batch).toarray()
        X2 = ipca.transform(X)
        labels = kmeans.predict(X)

        X_all.append(X2)
        y_all.extend(labels.tolist())

        seen += len(batch)
        if seen >= args.max_projects:
            break
        if seen >= next_log:
            print(f"  processed {seen} projects")
            next_log += LOG_THRESHOLD

    X_all = np.vstack(X_all)

    features = vec.get_feature_names_out()

    print("\n=== Cluster interpretation ===")

    cluster_names = {}

    for i, center in enumerate(kmeans.cluster_centers_):
        name = name_cluster(center, features)
        cluster_names[i] = name

        langs = top_languages(center, features)

        print(
            f"Cluster {i} [{name}]: "
            + ", ".join(langs)
        )


    scatter_clusters(
        X_all,
        y_all,
        out=args.out,
        title="ML Clusters of GitLab Projects by Languages",
        cluster_names=cluster_names
    )


if __name__ == "__main__":
    main()
