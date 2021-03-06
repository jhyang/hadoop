#!/usr/local/bin/python2.7
#
# tweetMapper.py
# This script gets tweets based on user levels and keywords 
# Output is a number of tweet options, but can also be raw JSON
# 

import argparse, json, os, re, string, sys, time

users    = {}
wordList = []

def formatDate(dateString):
    # Parse data in the format of Sat Mar 12 01:49:55 +0000 2011
    d  = string.split( dateString, ' ')
    ds = ' '.join([d[1], d[2], d[3], d[5] ])
    dt = time.strptime(ds, '%b %d %H:%M:%S %Y')
    return time.strftime('%Y-%m-%d %H:%M:%S', dt)

def rep(n, x):
    s = ''
    for i in range(0, n):
        s += x

    return s

def validate( x ):
    if x:
        if type(x) == unicode:
            x = string.replace(x, "\n", " ")
            x = string.replace(x, "\r", " ")
            x = string.replace(x, "\t", " ")
            return x.encode('utf-8')
        else:
            return str(x)
    else:
        return "0"

def loadUsers(levelFile):
    f = open(levelFile, 'r')
    for line in f:
        line = line.lower().strip()
        (user_id, level) = line.split("\t")

        if user_id == 'user_id':
            continue
        
        users[ user_id ] = level
    f.close()

def loadKeywords(path):
    f = open(path, 'r')
    for line in f:
        line = line.lower()
        wordList.append( line.strip() )
    f.close()

def main():
    punc  = '.,-'
    trans = rep(len(punc), ' ')

    parser = argparse.ArgumentParser(description = 
        """This script operates as the mapper part of MapReduce job. 
        Its output is tweets either in raw JSON or a number of fields,
        so the reducer will probably just be an Identity function.""")
    parser.add_argument('-a', '--all', action = "store_true", help = "Print out all tweets, no constraints")
    parser.add_argument('-k', '--keywordFile', default = None,
        help = "Path of keyword file. Use this to enable keyword matching.")
    parser.add_argument('-l','--level', choices = ['1', '2', '3' ,'all'])
    parser.add_argument('--levelFile', default = "follow-r3.txt")
    parser.add_argument('-r', '--retweet', action = "store_true", 
        help = "Include retweet information. Will output the same level of detail ")
    parser.add_argument('-t', '--tweetDetail', choices = ['low', 'medium', 'high'], default = 'low',
        help = """The level of detail in output. 'basic' includes status_id, timestamp, text, and basic user information.
        'moderate' includes more information, including user geolocation, user location, and user URL.
        'high' includes the most available information in the tweet.""")
    parser.add_argument('--hashtag', action = "store_true",
        help = "Instead of text, this outputs the hashtags.")
    parser.add_argument('-o', '--output', default="tab", choices = ['tab', 'json'],
        help = "Output format for the tweet.")
    parser.add_argument('--minUserFollowers', type = int,
        help = "Minimum number of followers that the user should have.")
    parser.add_argument('--minUserTweets', type = int,
        help = "Minimum number of tweets that the user should have.")

    args  = parser.parse_args()

    if args.keywordFile:
        loadKeywords( args.keywordFile )

    if args.level:
        loadUsers(args.levelFile)    

    for line in sys.stdin:
        line = line.strip()

        try:
            data = json.loads(line)
        except ValueError as detail:
            ## print the line when it messes up, but clean it up first
            #line = line.translate( string.maketrans( '\t\n\r', '   ') )
            #print "11111111 PARSE ERROR: " + line
            continue

        if not (isinstance(data, dict)):
            #print "DICT ERROR: " + data            
            pass
        elif 'delete' in data:
            #print data['delete']['status']['id']
            pass
        else:
            uid  = None
            sid  = None
            printThis = True
            
            retweet = data.get('retweeted_status', None)

            if 'id_str' in data:
                sid = data['id_str']
            else:
                sid = str(data['id'])

            if 'id_str' in data['user']:
                uid = data['user']['id_str']
            else:
                uid = str(data['user']['id'])

            if args.all:
                printThis = True                
            else:
                if args.level:
                    if uid in users and (args.level == 'all' or users[uid] == args.level):
                        printThis = printThis and True
                    else:
                        printThis = printThis and False

                 ## skip this tweet if user does not meet minimum number of followers
                if args.minUserFollowers:
                    if user['followers_count'] < args.minUserFollowers:
                        printThis = printThis and False

                ## skip this tweet if user does not meet minimum number of tweets
                if args.minUserTweets:
                    if user['statuses_count'] < args.minUserTweets:
                        printThis = printThis and False

                if args.keywordFile:
                    printWord = False
                    text = ''

                    if retweet:
                        text = retweet['text'].lower()
                    else:
                        text = data['text'].lower()
            
                    text = text.encode('utf-8')

                    for w in wordList:
                        if w in text:
                            printWord = True
                            break

                    printThis = printThis and printWord

            ## Print if all the prior conditions have been met
            if printThis:
                ## print tab separated if specified
                if args.output == 'json':
                    print sid, "\t", line
                else:
                    ## TK: This stuff is all for search API
                    # rt      = None
                    # rt_user = None
                    # rt_sn   = None

                    # if 'retweeted_status' in data:
                    #     if 'user' in data['retweeted_status']:
                    #         rt_user = data['retweeted_status']['user']['name']
                    #         rt_sn   = data['retweeted_status']['user']['screen_name']
                
                    ## elements to print
                    toPrint   = []

                    ## tweets to process
                    toProcess = [data]

                    if args.retweet and retweet:
                        toProcess.append(retweet)

                    for e in toProcess:
                        coords = None
                        u      = e['user']

                        ## calculate coordinates. specified in latitude then longitude.
                        if e['coordinates']:
                            coords = ",".join( map(str, reversed(e['coordinates']['coordinates'])) )                            
                        elif e['geo']:
                            coords = ",".join( map(str, e['geo']['coordinates']) )

                        if args.hashtag:
                            if len(e['entities']['hashtags']):
                                e['text'] = " ".join( map(lambda x: x['text'], e['entities']['hashtags']) )
                            else:
                                e['text'] = ""
                        else:
                            ## remove tabs and newlines from text
                            e['text'] = e['text'].encode('utf-8')
                            e['text'] = e['text'].translate( string.maketrans( '\t\n\r', '   ') )
                            e['text'] = e['text'].decode('utf-8')                        

                        userlevel = '0'
                        ## get the user level, if it exists
                        if u['id_str'] in users:
                            userlevel = users[ u['id_str'] ]

                        ## print rather basic stuff
                        if args.tweetDetail == 'low':
                            toPrint.extend([
                                e['id_str'], 
                                formatDate( e['created_at'] ),
                                e['text'], 
                                u['id_str'], 
                                u['name'], 
                                u['screen_name'],
                                userlevel
                            ])
                        elif args.tweetDetail == 'medium':                            
                            toPrint.extend([
                                e['id_str'], 
                                formatDate( e['created_at'] ),
                                e['text'],
                                e['source'],
                                coords,
                                u['id_str'], 
                                u['name'], 
                                u['screen_name'],
                                userlevel,
                                u['description'],
                                u['location'],
                                u['url']
                            ])
                        elif args.tweetDetail == 'high':
                            toPrint.extend([
                                e['id_str'], 
                                formatDate( e['created_at'] ),
                                e['text'],
                                e['source'],
                                coords,
                                u['id_str'], 
                                u['name'], 
                                u['screen_name'],
                                userlevel,
                                u['description'],
                                u['location'],
                                u['url'],
                                u['followers_count'],
                                u['friends_count'],
                                u['listed_count'],
                                u['statuses_count']
                            ])

                    print "\t".join( map(validate, toPrint) )

                    

if __name__ == '__main__':
    main()
    
