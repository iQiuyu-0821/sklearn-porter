# -*- coding: utf-8 -*-

from sklearn.tree.tree import DecisionTreeClassifier

from ...Template import Template


class RandomForestClassifier(Template):
    """
    See also
    --------
    sklearn.ensemble.RandomForestClassifier

    http://scikit-learn.org/0.18/modules/generated/sklearn.ensemble.RandomForestClassifier.html
    """

    SUPPORTED_METHODS = ['predict']
    SUPPORTED_LANGUAGES = ['c', 'java', 'js']

    # @formatter:off
    TEMPLATES = {
        'c': {
            'if':       'if (atts[{0}] {1} {2}) {{',
            'else':     '} else {',
            'endif':    '}',
            'arr':      'classes[{0}] = {1}',
            'indent':   '    ',
            'join':     '; ',
        },
        'java': {
            'if':       'if (atts[{0}] {1} {2}) {{',
            'else':     '} else {',
            'endif':    '}',
            'arr':      'classes[{0}] = {1}',
            'indent':   '    ',
            'join':     '; ',
        },
        'js': {
            'if':       'if (atts[{0}] {1} {2}) {{',
            'else':     '} else {',
            'endif':    '}',
            'arr':      'classes[{0}] = {1}',
            'indent':   '    ',
            'join':     '; ',
        }
    }
    # @formatter:on

    def __init__(self, model, target_language='java', target_method='predict', **kwargs):
        super(RandomForestClassifier, self).__init__(model, target_language=target_language, target_method=target_method, **kwargs)
        self.model = model

        # Check type of base estimators:
        if not isinstance(model.base_estimator, DecisionTreeClassifier):
            msg = "The classifier doesn't support the given base estimator %s."
            raise ValueError(msg, model.base_estimator)

        # Check number of base estimators:
        if not model.n_estimators > 0:
            msg = "The classifier hasn't any base estimators."
            raise ValueError(msg)

        self.n_classes = model.n_classes_
        self.models = []
        self.n_estimators = 0
        for idx in range(self.model.n_estimators):
            self.models.append(self.model.estimators_[idx])
            self.n_estimators += 1
            self.n_features = self.model.estimators_[idx].n_features_

    def export(self, class_name, method_name):
        """
        Port a trained model to the syntax of a chosen programming language.

        Parameters
        ----------
        :param model : AdaBoostClassifier
            An instance of a trained AdaBoostClassifier model.
        """
        self.class_name = class_name
        self.method_name = method_name
        if self.target_method == 'predict':
            return self.predict()

    def predict(self):
        """
        Port the predict method.

        Returns
        -------
        :return: out : string
            The ported predict method.
        """
        return self.create_class(self.create_method())

    def create_branches(self, l, r, t, value, features, node, depth):
        """
        Parse and port a single tree model.

        Parameters
        ----------
        :param l : object
            The left children node.
        :param r : object
            The left children node.
        :param t : object
            The decision threshold.
        :param value : object
            The label or class.
        :param features : object
            The feature values.
        :param node : int
            The current node.
        :param depth : int
            The tree depth.

        Returns
        -------
        :return : string
            The ported single tree as function or method.
        """
        out = ''  # returned output
        # ind = '\n' + '    ' * depth
        if t[node] != -2.:
            out += '\n'
            out += self.temp('if', n_indents=depth).format(
                features[node], '<=', repr(t[node]))
            if l[node] != -1.:
                out += self.create_branches(
                    l, r, t, value, features, l[node], depth + 1)
            out += '\n'
            out += self.temp('else', n_indents=depth)
            if r[node] != -1.:
                out += self.create_branches(
                    l, r, t, value, features, r[node], depth + 1)
            out += '\n'
            out += self.temp('endif', n_indents=depth)
        else:
            clazzes = []
            for i, rate in enumerate(value[node][0]):
                clazz = self.temp('arr', n_indents=depth).format(i, int(rate))
                clazz = '\n' + clazz
                clazzes.append(clazz)
            out += self.temp('join').join(clazzes) + self.temp('join')
        return out

    def create_single_method(self, model_index, model):
        """
        Port a method for a single tree.

        Parameters
        ----------
        :param model_index : int
            The model index.
        :param model : RandomForestClassifier
            The model.

        Returns
        -------
        :return : string
            The created method.
        """
        indices = []
        for i in model.tree_.feature:
            n_features = model.n_features_
            if self.n_features > 1 or (self.n_features == 1 and i >= 0):
                indices.append([str(j) for j in range(n_features)][i])

        tree_branches = self.create_branches(
            model.tree_.children_left, model.tree_.children_right,
            model.tree_.threshold, model.tree_.value, indices, 0, 1)

        suffix = ("{0:0" + str(len(str(self.n_estimators - 1))) + "d}")
        model_index = suffix.format(int(model_index))

        return self.temp('single_method').format(
            model_index, self.method_name, self.n_classes, tree_branches)

    def create_method(self):
        """
        Build the model methods or functions.

        Returns
        -------
        :return out : string
            The built methods as merged string.
        """
        # Generate method or function names:
        fn_names = []
        suffix = ("_{0:0" + str(len(str(self.n_estimators - 1))) + "d}")
        for idx, model in enumerate(self.models):
            fn_name = self.method_name + suffix.format(idx)
            fn_name = self.temp(
                'method_calls', n_indents=2, skipping=True).format(
                idx, self.class_name, fn_name)
            fn_names.append(fn_name)
        fn_names = '\n'.join(fn_names)
        fn_names = self.indent(fn_names, n_indents=1, skipping=True)

        # Generate related trees:
        fns = []
        for idx, model in enumerate(self.models):
            tree = self.create_single_method(idx, model)
            fns.append(tree)
        fns = '\n'.join(fns)

        # Merge generated content:
        n_indents = 1 if self.target_language in ['java', 'js'] else 0
        method = self.temp('method').format(
            fns, self.method_name, self.n_estimators, self.n_classes, fn_names)
        method = self.indent(method, n_indents=n_indents, skipping=True)
        return method

    def create_class(self, method):
        """
        Build the model class.

        Returns
        -------
        :return out : string
            The built class as string.
        """
        return self.temp('class').format(
            self.class_name, self.method_name, method, self.n_features)
