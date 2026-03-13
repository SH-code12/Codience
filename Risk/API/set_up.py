# import pandas as pd
import statistics
import math



class commit_files:
  def __init__(self,nf,lines_per_file,files_last_modified):
    self.nf = nf # number of files
    self.lines_per_file = lines_per_file #List of Number of Modified Lines in every file
    self.files_last_modified = files_last_modified # List that contains which commits last modified each file.

  def get_lines_per_file(self):
    return self.lines_per_file

  def get_files_last_modified(self):
    return self.files_last_modified

  def get_nf(self):
    return self.nf

  def nuc(self):
      """
      Input: List of the last commit that modified the files
      Output: the number of unique last changes of the modified files.
      """
      return len(set(self.files_last_modified))

class developer_commit:
    def __init__(self, ndev, exp, rexp, sexp):
        self._ndev = ndev
        self._exp = exp
        self._rexp = rexp
        self._sexp = sexp

    def ndev(self):
        return self._ndev

    def exp(self):
        return self._exp

    def rexp(self):
        return self._rexp

    def sexp(self):
        return self._sexp


class commit:
    def __init__(self, ns, nd, nf, la, ld, lt, cf):
        self.ns = ns  # number of subsystems
        self.nd = nd  # number of directories
        self.la = la  # number of lines added
        self.ld = ld  # number of lines deleted
        self.lt = lt  # total number of lines before change
        self.cf = cf  # commit files

    def get_ns(self):
        return self.ns

    def get_nd(self):
        return self.nd

    def get_la(self):
        return self.la

    def get_ld(self):
        return self.ld

    def Entropy(self):
        """
        Input: List of Number of Modified Lines in every file
        Output: Entropy Feature
        """
        p = self.cf.get_lines_per_file()

        total = sum(p)
        s = 0
        for i in range(len(p)):
            ratio = p[i] / total
            s -= ratio * math.log(ratio, 2)
        return s / math.log(len(p),2)

    def age(self):
        """n
        Input: List of when was the files last modified
        Output: Age Feature
        """

        return statistics.mean(self.cf.age())

    def nuc(self):
        return self.cf.nuc()




