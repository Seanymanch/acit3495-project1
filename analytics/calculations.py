"""Pure function, easy to test independently of any database."""
def summarize(values):
    values=list(values)
    if not values:
        return {'count':0,'minimum':None,'maximum':None,'average':None}
    return {'count':len(values),'minimum':min(values),'maximum':max(values),
            'average':sum(values)/len(values)}
