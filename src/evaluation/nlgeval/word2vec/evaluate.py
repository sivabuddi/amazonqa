# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT license. See LICENSE.md file in the project root for full license information.
import os
import numpy as np
from tqdm import tqdm
try:
    from gensim.models import KeyedVectors
except ImportError:
    from gensim.models import Word2Vec as KeyedVectors


class Embedding(object):
    def __init__(self):
        path = os.environ.get('NLGEVAL_DATA', os.path.join(os.path.dirname(__file__), '..', 'data'))
        self.m = KeyedVectors.load(os.path.join(path, 'glove.6B.300d.model.bin'), mmap='r')
        try:
            self.unk = self.m.vectors.mean(axis=0)
        except AttributeError:
            self.unk = self.m.syn0.mean(axis=0)

    @property
    def w2v(self):
        return np.concatenate((self.m.syn0, self.unk[None,:]), axis=0)

    def __getitem__(self, key):
        try:
            return self.m.vocab[key].index
        except KeyError:
            return len(self.m.syn0)

    def vec(self, key):
        try:
            vectors = self.m.vectors
        except AttributeError:
            vectors = self.m.syn0
        try:
            return vectors[self.m.vocab[key].index]
        except KeyError:
            return self.unk


def eval_emb_metrics(hypothesis, references, emb=None, metrics_to_omit=None, multiple=False):
    from sklearn.metrics.pairwise import cosine_similarity
    from nltk.tokenize import word_tokenize
    import numpy as np
    if emb is None:
        emb = Embedding()

    if metrics_to_omit is None:
        metrics_to_omit = set()

    emb_hyps = []
    avg_emb_hyps = []
    extreme_emb_hyps = []
    for hyp in tqdm(hypothesis):
        embs = [emb.vec(word) for word in word_tokenize(hyp)]

        avg_emb = np.sum(embs, axis=0) / np.linalg.norm(np.sum(embs, axis=0))
        assert not np.any(np.isnan(avg_emb))

        maxemb = np.max(embs, axis=0)
        minemb = np.min(embs, axis=0)
        extreme_emb = list(map(lambda x, y: x if ((x>y or x<-y) and y>0) or ((x<y or x>-y) and y<0) else y, maxemb, minemb))

        emb_hyps.append(embs)
        avg_emb_hyps.append(avg_emb)
        extreme_emb_hyps.append(extreme_emb)

    emb_refs = []
    avg_emb_refs = []
    extreme_emb_refs = []
    for refsource in tqdm(references):
        emb_refsource = []
        avg_emb_refsource = []
        extreme_emb_refsource = []
        for ref in refsource:
            embs = [emb.vec(word) for word in word_tokenize(ref)]

            avg_emb = np.sum(embs, axis=0) / np.linalg.norm(np.sum(embs, axis=0))
            assert not np.any(np.isnan(avg_emb))

            maxemb = np.max(embs, axis=0)
            minemb = np.min(embs, axis=0)
            extreme_emb = list(map(lambda x, y: x if ((x>y or x<-y) and y>0) or ((x<y or x>-y) and y<0) else y, maxemb, minemb))

            emb_refsource.append(embs)
            avg_emb_refsource.append(avg_emb)
            extreme_emb_refsource.append(extreme_emb)
        emb_refs.append(emb_refsource)
        avg_emb_refs.append(avg_emb_refsource)
        extreme_emb_refs.append(extreme_emb_refsource)

    rval = {}
    if 'EmbeddingAverageCosineSimilairty' not in metrics_to_omit:
        print('\tComputing EmbeddingAverageCosineSimilairty...')
        cos_similarity = list(map(lambda refv: cosine_similarity(refv, avg_emb_hyps).diagonal(), avg_emb_refs))
        cos_similarity = np.array([np.max(i) for i in cos_similarity])
        if not multiple:
            cos_similarity = cos_similarity.mean()
        rval['EmbeddingAverageCosineSimilairty'] = cos_similarity

    if 'VectorExtremaCosineSimilarity' not in metrics_to_omit:
        print('\tComputing VectorExtremaCosineSimilarity...')
        cos_similarity = list(map(lambda refv: cosine_similarity(refv, extreme_emb_hyps).diagonal(), extreme_emb_refs))
        cos_similarity = np.array([np.max(i) for i in cos_similarity])
        if not multiple:
            cos_similarity = cos_similarity.mean()
        rval['VectorExtremaCosineSimilarity'] = cos_similarity

    if 'GreedyMatchingScore' not in metrics_to_omit:
        scores = []
        print('\tComputing GreedyMatchingScore...')
        for emb_refsource in tqdm(emb_refs):
            score_source = []
            for emb_ref, emb_hyp in zip(emb_refsource, emb_hyps):
                simi_matrix = cosine_similarity(emb_ref, emb_hyp)
                dir1 = simi_matrix.max(axis=0).mean()
                dir2 = simi_matrix.max(axis=1).mean()
                score_source.append((dir1 + dir2) / 2)
            scores.append(score_source)
        scores = np.array([np.max(i) for i in scores])
        if not multiple:
            scores = scores.mean()
        rval['GreedyMatchingScore'] = scores

    return rval

if __name__ == '__main__':
    emb = Embedding()
