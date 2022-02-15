This repo contains a python script that reads a schedule from a pdf and then adds the times to a google calendar.

Currently supports the pdf schedule format used by Kungälv municipal (might work for other Swedish municipals as well).
The pdf needs to have a format like this:

 <img width="619" alt="Screenshot 2022-02-15 at 22 54 37" src="https://user-images.githubusercontent.com/5288515/154155943-30620181-b966-45cf-81df-f3b4ae070ccd.png">


A **settings.yaml** file must be created in the root folder. That should at least contain:

    googleCalendarLink: "link-to-google-calendar" # This one will probably work in most cases: "https://www.googleapis.com/auth/calendar"
    calendarId: "id-of-the-calendar-where-the-events-shall-be-added"

The settings.yaml file may also contain:


    pickUpDropOff: A dictionary with keys for weekdays (e.g. "Monday") and as value a list which contains one or everal rules. 
A rule could for example be: 

    {"weeks": "all","info": "Anna drops off\nAnders picks up"}

"weeks" could contain the values "all", "even" or "odd". The key "attendees" could also be included in the rule, the value of that should then be a list of dictionarys each containg the key "email" and the attendees email as a value. The attendees would then be invited to the event.
A full example:

    pickUpDropOff: {
     "Monday": [{"weeks": "all","info": "Anna drops off\nAnders picks up"}],
     "Tuesday": [{"weeks": "all","info": "Anders drops off\Anna picks up"}],
     "Thursday": [{"weeks": "odd","info": "Anders drops off\Anna picks up"},
                  {"weeks": "even",
                   "info": "Anders drops off\Grandpa & grandma picks up",
                   "attendees": [{"email": "grandpa@email.com"}, 
                                 {"email": "grandma@email.com"}]}],

   }

The Google Calendar API must be activated and added to your account. A good guide to follow: https://karenapp.io/articles/how-to-automate-google-calendar-with-python-using-the-calendar-api/
