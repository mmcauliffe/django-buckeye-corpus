from django.db import models,connection,transaction

def chunks(l, n):
    """ Yield successive n-sized chunks from l.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

class BulkManager(models.Manager):
    tbl_name = "tbl_name"
    cols = ['one','two','three']

    def create_in_bulk(self,values):
        sql = "INSERT INTO %s (%s) VALUES (%s)" % (self.tbl_name,','.join(self.cols),','.join(['%s' for i in range(len(self.cols))]))
        splitted = chunks(values,50000)
        curs = connection.cursor()
        for l in splitted:
            curs.executemany(sql, l)
            transaction.commit_unless_managed()
