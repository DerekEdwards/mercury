from cxze.tracad import models
from cxze import ridecell_config
from django.core.mail import EmailMessage

import datetime


def main():
    """
    This function is called everytime the script is run. It gets all the web and voicemail
    feedbacks left by the users since the previous day. If there are any feedbacks then the message
    content and audio url along with user name and details are sent as email.
    """
    now = datetime.datetime.now()
    start_date_time = now - datetime.timedelta(days=1)
    web_feedbacks = models.UserFeedback.objects.filter(timestamp__gte=start_date_time)
    voicemail_feedbacks = models.FeedBackMessages.objects.filter(timestamp__gte=start_date_time)
    
    if (web_feedbacks.count() >= 1) or (voicemail_feedbacks.count() >= 1):
        subject = 'MARTA user feedback for %s to %s'
        subject = subject % (start_date_time.strftime("%d-%b-%Y"),
                             now.strftime("%d-%b-%Y"))
        body = ''
        for feedback in web_feedbacks:
            body += "\nReported by username(user_id): %s (%d)"
            if not feedback.user:
                body = body  % ("Anonymous", -1)
            else:
                body = body % (feedback.user.username, feedback.user.id)
                
            body += "\t at: %s\n" % (feedback.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            body += "Message: %s\n" % (feedback.feedback)
            body += ("-" * 50)

        if body:
            body += "\n\n\n"

        for feedback in voicemail_feedbacks:
            user_profiles = models.EndUserProfile.objects.filter(phone_number = feedback.caller)
            body += '\nReported by phone_number: %s ' % (feedback.caller)
            if user_profiles.count() >= 1:
                body += ' - username(user_id): '
                for user_profile in user_profiles:
                    body += "%s (%d)," % (user_profile.user.username, user_profile.user.id)
                body = body.strip(",")                    
                    
            body += '\nFeedback audio URL: %s\tat: %s\n' % (feedback.audio_url, feedback.timestamp.strftime("%Y-%m-%d %H:%M:%S"))
            body += ("-" * 50)
        

        email = EmailMessage(subject, body, 'core@ridecell.com', ['support@ridecell.com'],
                             [], headers = {'Reply-To': 'core@ridecell.com'})
        email.send(fail_silently=False)
                                              
    return


if __name__=='__main__':
    main()
