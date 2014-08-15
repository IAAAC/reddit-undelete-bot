import praw
from time import time, sleep
from requests.exceptions import HTTPError

# global reddit session
r = None

def login():
    global r
    user_agent=('undelete bot version 0.2 by /u/IAmAnAnonymousCoward')
    user='*****'
    password='*****'
    r = praw.Reddit(user_agent=user_agent)
    r.config.decode_html_entities = True
    while True:
        try:
            r.login(user, password)
            break
        except Exception as e:
            print 'can\'t even log in'
            print type(e), e
            sleep(10)

def get_top_submissions():
    global r
    top_submissions = []
    unique_ids = set()
    monitored_subreddit='all'
    while True:
        try:
            top_submissions_generator = r.get_subreddit(monitored_subreddit).get_hot(limit=1100)
            # actually fetch them NOW
            for submission in top_submissions_generator:
                # due to the dynamic nature of reddit
                # there is a high risk that we might get some submissions twice
                # avoid that by making sure ids are unique
                # at the same time there's a high risk to miss some submissions
                # this is what leads to false alarms later
                if submission.id not in unique_ids:
                    top_submissions.append(submission)
                    unique_ids.add(submission.id)
            break
        except Exception as e:
            print 'Exception fetching the top submissions'
            print type(e), e
            sleep(10)
    return top_submissions

def find_removed_submissions(new_submissions,old_submissions,old_false_alarm_submissions):
    missing_submissions = []
    for old_submission in old_submissions:
        found = False
        for new_submission in new_submissions:
            if new_submission.id == old_submission.id:
                found = True
                break
        # don't bother if it's porn
        if found == False and not is_porn(old_submission):
            missing_submissions.append(old_submission)

    removed_submissions = []
    false_alarm_submissions = []

    # for every missing submission
    # removal must be confirmed
    # if it can't be confirmed
    # it must often be counted as false alarm
    for missing_submission in missing_submissions:
        removal_status = confirm_removal(missing_submission)
        if removal_status == True:
            removed_submissions.append(missing_submission)
        elif removal_status == False:
            false_alarm_submissions.append(missing_submission)
        else:
            pass

    # removed_submissions, false_alarm_submissions = confirm_removal(removed_submissions)
    
    # add false alarms to new_submissions, because we know that they should be there
    # otherwise there is a risk of false negatives in the next cycle because a
    # submission might now actually be removed, but we're not looking for it
    # their spot in old_submissions is best guess for spot in new_submissions
    for submission in false_alarm_submissions:
        # don't add if it was already added last time
        # prevents submissions from getting stuck
        if submission not in old_false_alarm_submissions:
            rank = old_submissions.index(submission)
            new_submissions.insert(rank,submission)
            
    return removed_submissions, new_submissions, false_alarm_submissions

def confirm_removal(missing_submission):
    # fetch submission again if user wasn't deleted before submission disappeared
    if missing_submission.author != None:
        while True:
            try:
                newly_fetched_submission = r.get_submission(submission_id=missing_submission.id)
                break
            except HTTPError as e:
                # 403: Forbidden means subreddit went private
                # Therefore submission wasn't deleted by user
                if e.response.status_code == 403:
                    print '{0} went private?!'.format(missing_submission.subreddit.display_name)
                    return True
                # 404: Not Found means subreddit was banned
                # Therefore submission wasn't deleted by user
                # But better play it safe and don't undelete
                # Don't count as false alarm either
                if e.response.status_code == 404:
                    print '{0} was banned?!'.format(missing_submission.subreddit.display_name)
                    return None                                    
            except Exception as e:
                print 'Exception while fetching missing submission'
                print type(e), e
                sleep(10)
                
    # check if user deleted it
    # if so, don't undelete
    # but don't count as false alarm either
    if missing_submission.author != None and newly_fetched_submission.author == None:
            return None

    # search for author, if it's there and doesn't contain a dash
    if missing_submission.author != None and '-' not in missing_submission.author.name:
        search_string = 'author:{0}'.format(missing_submission.author.name)
        display_name = missing_submission.subreddit.display_name
        while True:
            try:
                search = r.search(search_string, sort='new', subreddit=display_name, limit=100)
                for submission in search:
                    if submission.id == missing_submission.id:
                        # submission found means it was a false alarm
                        return False
                break
            except Exception as e:
                print 'Exception while searching for author /u/{0}'.format(missing_submission.author.name)
                print type(e), e
                sleep(30)
                     
    # should limit to top 100 to prevent further problems
    # but /r/funny submission in the top 1000 of /r/all
    # might not be in top 100 of /r/funny!
    else:
        display_name = missing_submission.subreddit.display_name
        while True:
            try:
                submissions = r.get_subreddit(display_name).get_hot(limit=100)
                for submission in submissions:
                    if submission.id == missing_submission.id:
                        # submission found means it was a false alarm
                        return False
                break
            except Exception as e:
                print 'Exception while searching top submissions in {0}'.format(display_name)
                print type(e), e
                sleep(30)

    # If submission hasn't been found by now, it must have been removed
    return True

def is_porn(submission):
    if not submission.over_18:
        return False
    display_name = submission.subreddit.display_name
    top_porn_subreddits = ['gonewild','RealGirls','nsfw','gonewildcurvy','NSFW_GIF','ass','ladybonersgw',
                       'BustyPetite','nsfw_gifs','Amateur','cumsluts','GoneWildPlus','rule34','Boobies',
                       'milf','curvy', 'asstastic','OnOff','girlsinyogapants','AsiansGoneWild','AsianHotties',
                       'GoneMild','Hotchickswithtattoos','PetiteGoneWild','tightdresses','redheads','yiff',
                       'ginger','thick','hugeboobs','anal','BigBoobsGW','Stacked','hentai','pussy','TinyTits',
                       'nsfwhardcore','palegirls','Bondage','Blowjobs','GWCouples','burstingout',
                       'HappyEmbarassedGirls','TittyDrop','MassiveCock','holdthemoan','wifesharing','rearpussy',
                       'GirlswithGlasses','GaybrosGoneWild','boltedontits','LegalTeens','dirtysmall','asshole',
                       'juicyasians','randomsexiness','NSFWFunny','penis','workgonewild','datgap',
                       'GirlsFinishingTheJob','pornvids','gonewildcolor','lingerie','grool','Tgirls',
                       'FacebookCleavage','latinas','celebnsfw']
    if display_name in top_porn_subreddits:
        return True
    nsfw_but_not_porn = ['ImGoingToHellForThis','MorbidReality','watchpeopledie','GreatApes','Gore','DarkNetMarkets']
    if display_name in nsfw_but_not_porn:
        return False
    # if that didn't work, we must fetch the subreddit
    while True:
        try:
            return submission.subreddit.over18
        except Exception as e:
            print 'Exception while fetching subreddit to determine NSFW status'
            print type(e), e
            sleep(5)

def undelete_removed_submissions(removed_submissions,old_submissions):
    # old_submissions needed for rank
    # list of removed submissions could just be index numbers
    # instead of full copies
    
    for submission in removed_submissions:
        rank = old_submissions.index(submission)+1
        score = submission.score
        num_comments = submission.num_comments
        subreddit = submission.subreddit.display_name
        title = u'[#{0}|+{1}|{2}] {3}'
        title = title.format(str(rank),str(score),str(num_comments),submission.title)
        length = len(title) + len(subreddit) + 6 
        if length > 300:
            excess = length - 300 + 3
            title = title[0:-excess] + '...'
        title = title + ' [/r/{0}]'.format(subreddit)

        bot_submission = None
        while True:
            try:
                bot_submission = r.submit('*****', title, url=submission.permalink)
                break
            # don't undelete a submission twice
            except praw.errors.AlreadySubmitted:
                print '{0} already submitted'.format(submission.permalink)
                bot_submission =  None
                break
            except Exception as e:
                print 'Exception while posting'
                print type(e), e
                sleep(5)
        if submission.selftext != '' and bot_submission !=  None:
            undelete_selftext(bot_submission,submission.selftext)
        
def undelete_selftext(bot_submission,selftext):
    selftext = u'>' + selftext.replace('\n','\n>')                                  
    lines = selftext.splitlines(True)
    # use multiple comments if necessary
    # to backup the whole selftext
    comments = []
    comment = u""   
    for line in lines:
        # handle selftext with no line breaks
        if len(line) > 10000:
            line = line[:9997] + '...'
        # cram in as many lines in each comment as possible
        if len(comment + line) <= 10000:
            comment = comment + line 
        else:
            comments.append(comment)
            comment = line
    # don't forget the last comment
    comments.append(comment)
    # post comments
    parent_comment = None
    for comment in comments:
        if parent_comment == None:
            parent_comment = bot_submission.add_comment(comment)
        else:
            parent_comment = parent_comment.reply(comment)
            
def initialize():
    top_submissions = get_top_submissions()
    top_submissions = top_submissions[0:-100]
    sleep(30)
    return top_submissions
        
def main():
    global r
    
    login()
    old_top_submissions = initialize()   
    false_positives = []
    
    while True:
        try:
            top_submissions = get_top_submissions()
            removed_submissions, top_submissions, false_positives = find_removed_submissions(top_submissions,old_top_submissions,false_positives)
            undelete_removed_submissions(removed_submissions,old_top_submissions)
            
            old_top_submissions = top_submissions[0:-100]
            
            sleep(30)
        except KeyboardInterrupt:
            raise
        # this shouldn't happen
        except Exception as e:
            print 'Exception while in main function, HOW?!'
            print type(e), e
            # re-initialize, just to be sure
            old_top_submissions = initialize()
            false_positives = []
            
if __name__ == "__main__":
    main()
