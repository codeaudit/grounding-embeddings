import codecs
from collections import defaultdict, namedtuple
from pathlib import Path
from pprint import pprint

import numpy as np


EMBEDDING_NAME = "glove.6B.300d"
GLOVE_INPUT = "../glove/%s.txt" % EMBEDDING_NAME

FEATURES = "./all/CONCS_FEATS_concstats_brm.txt"
VOCAB = "./all/vocab.txt"
EMBEDDINGS = "./all/embeddings.%s.npy" % EMBEDDING_NAME
OUTPUT = "./all/feature_fit.txt"


Feature = namedtuple("Feature", ["name", "concepts", "wb_label", "wb_maj",
                                 "wb_min", "br_label", "disting"])


def load_embeddings(concepts):
    if Path(EMBEDDINGS).is_file():
        embeddings = np.load(EMBEDDINGS)

        assert Path(VOCAB).is_file()
        with open(VOCAB, "r") as vocab_f:
            vocab = [line.strip() for line in vocab_f]
        assert len(embeddings) == len(vocab), "%i %i" % (len(embeddings), len(vocab))
    else:
        vocab, embeddings = [], []
        with codecs.open(GLOVE_INPUT, "r", encoding="utf-8") as glove_f:
            for line in glove_f:
                fields = line.strip().split()
                word = fields[0]
                if word in concepts:
                    vec = [float(x) for x in fields[1:]]
                    embeddings.append(vec)
                    vocab.append(word)

        embeddings = np.array(embeddings)
        np.save(EMBEDDINGS, embeddings)

        with open(VOCAB, "w") as vocab_f:
            vocab_f.write("\n".join(vocab))

    return vocab, embeddings


def load_features_concepts():
    """
    Returns:
        features: string -> Feature
        concepts: set of strings
    """
    features = {}
    concepts = set()

    with open(FEATURES, "r") as features_f:
        for line in features_f:
            fields = line.strip().split("\t")
            concept_name, feature_name = fields[:2]
            if feature_name not in features:
                features[feature_name] = Feature(
                        feature_name, set(), *fields[2:6], fields[10])

            features[feature_name].concepts.add(concept_name)
            concepts.add(concept_name)

    lengths = [len(f.concepts) for f in features.values()]
    from collections import Counter
    from pprint import pprint
    print("# of features with particular number of associated concepts:")
    pprint(Counter(lengths))

    return features, concepts


def analyze_feature(feature, features, word2idx, embeddings):
    # Fetch available embeddings.
    embeddings = [embeddings[word2idx[concept]]
                  for concept in features[feature].concepts
                  if concept in word2idx]
    if len(embeddings) < 4 or len(embeddings) > 7:
        return
    embeddings = np.asarray(embeddings)
    embeddings /= np.linalg.norm(embeddings, axis=1, keepdims=True)
    mean = np.mean(embeddings, axis=0)
    mean /= np.linalg.norm(mean)

    avg_dot = np.dot(embeddings, mean).mean()
    return (feature, len(embeddings), avg_dot)


def main():
    features, concepts = load_features_concepts()
    vocab, embeddings = load_embeddings(concepts)
    word2idx = {w: i for i, w in enumerate(vocab)}

    feature_data = [analyze_feature(feature, features, word2idx, embeddings)
                    for feature in features]
    feature_data = sorted(filter(None, feature_data), key=lambda f: f[2])

    label_groups = defaultdict(list)
    for name, n_entries, score in feature_data:
        print("%40s\t%i\t%f" % (name, n_entries, score))
        label_groups[features[name].br_label].append(score)

    print("\n\nGrouping by BR label:")
    label_groups = {k: (len(data), np.mean(data), np.var(data))
                    for k, data in label_groups.items()}
    label_groups = sorted(label_groups.items(), key=lambda x: x[1][1])
    for label_group, (n, mean, var) in label_groups:
        print("%25s\t%2i\t%.5f\t%.5f" % (label_group, n, mean, var))


if __name__ == "__main__":
    main()
