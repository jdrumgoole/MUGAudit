'''
Created on 7 Jul 2017

@author: jdrumgoole
'''
from dateutil.relativedelta import relativedelta
from datetime import datetime
 
from mongodb_utils.agg import Agg, CursorFormatter
from mugalyser.audit import Audit
from mugalyser.groups import EU_COUNTRIES,  Groups
from mugalyser.members import Members
from mugalyser.events import PastEvents

class MUG_Analytics( object ):
            
    def __init__(self, mdb, output_filename="-", formatter="json", batchID=None, limit=None, view=None ):
        self._mdb = mdb
        audit = Audit( mdb )
    

        self._sorter = None
        self._start_date = None
        self._end_date = None
        self._filename = output_filename
        self._format = formatter
        self._files = []
        self._limit = limit

        self._view = view
        if batchID is None:
            self._batchID = audit.get_last_valid_batch_id()
        else:
            self._batchID = batchID
            
        self._pro_account = audit.isProBatch( self._batchID )
    
    def files(self):
        return self._files
    
    def setRange(self, start_date, end_date ):
        self._start_date = start_date
        self._end_date = end_date      
        
    def setSort(self, sorter ):
        self._sorter = sorter
        
    def getMembers( self, urls, filename=None ):
        '''
        Get a count of the members for each group in "urls"
        Range doens't make sense here so its not used. If supplied it is ignored.
        '''
        
        agg = Agg( self._mdb.groupsCollection())
        
        agg.addMatch({ "batchID"       : { "$in" : [ self._batchID ]},
                       "group.urlname" : { "$in" : urls }} )
         
        agg.addProject(  { "_id" : 0, 
                           "urlname" : "$group.urlname", 
                           "country" : "$group.country",
                           "batchID" : 1, 
                           "member_count" : "$group.member_count" })
        
        if self._sorter:
            agg.addSort( self._sorter)
            
        if filename :
            self._filename = filename

        if self._view :
            agg.create_view( self._mdb.database(), "member_view" )
            #agg.create_view( self._mdb.database(), "members_view")
            
        formatter = CursorFormatter( agg.aggregate(), self._filename, self._format )
        formatter.output( fieldNames= [ "urlname", "country", "batchID", "member_count"] )
        
    def get_RSVP_history(self, urls, filename=None ):
        '''
        Get the list of past events for groups (urls) and report on the date of the event
        and the number of RSVPs.
        '''
                
        agg = Agg( self._mdb.pastEventsCollection())  
        
        agg.addMatch( { "batchID"             : self._batchID, 
                        "event.group.urlname" : { "$in" : urls }} )
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "event.time", self._start_date, self._end_date )
            
        agg.addProject( { "_id"        : 0,
                          "timestamp"  : "$event.time",
                          "urlname"    : "$event.group.urlname",
                          "event"      : "$event.name",
                          "rsvp_count" : "$event.yes_rsvp_count" } )
        
#         agg.addMatch( { "timestamp" : { "$type" : "date" }} )
#         agg.addGroup( { "_id" :"$timestamp",
#                         #"event" : { "$addToSet" : { "event" : "$event", "country" : "$country" }},
#                         "rsvp_count" : { "$sum" : "$rsvp_count"}})
        
        if self._sorter :
            agg.addSort( self._sorter)
            
        if filename :
            self._filename = filename
            
        if self._view :
            agg.create_view( self._mdb.database(), "rsvps_view" )
            
        formatter = CursorFormatter( agg.aggregate(), self._filename, self._format )
        filename = formatter.output( fieldNames= [ "timestamp", "urlname", "event","rsvp_count" ], datemap=[ "timestamp" ], limit=self._limit )
        
        if filename != "-":
            self._files.append( filename )

    def get_member_history(self, urls, filename=None ):
        '''
        Got into every batch and see what the member count was for each group (URL) this uses all 
        the batches to get a history of a group.
        Range is used to select batches in this case via the "timestamp" field.
        '''
        audit = Audit( self._mdb )
        
        validBatches = list( audit.get_valid_batch_ids())
                
        agg = Agg( self._mdb.groupsCollection())
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "timestamp", self._start_date, self._end_date )
        
        agg.addMatch({ "batchID"       : { "$in" : validBatches },
                       "group.urlname" : { "$in" : urls }} )
        
        agg.addProject({ "_id": 0,
                        "timestamp" : 1,
                         "batchID"  : 1,
                         "urlname"  : "$group.urlname",
                         "count"    : "$group.members" })


        

#         agg.addGroup( { "_id"    : { "ts": "$timestamp", "batchID" : "$batchID" },
#                         "groups" : { "$addToSet" : "$urlname" },
#                         "count"  : { "$sum" : "$count"}})
#         
        #CursorFormatter( agg.aggregate()).output()
        
        if self._sorter :
            agg.addSort( self._sorter)
            
        #CursorFormatter( agg.aggregate()).output()
        if filename :
            self._filename = filename
            
        if self._view :
            agg.create_view( self._mdb.database(), "groups_view" )
            
        formatter = CursorFormatter( agg.aggregate(), self._filename, self._format )
        formatter.output( fieldNames= [ "timestamp", "batchID", "urlname", "count" ], datemap=[ "timestamp" ], limit=self._limit)
    
        if filename != "-":
            self._files.append( filename )
            
    def get_group_names( self, region_arg ):
        
        groups = Groups( self._mdb )
        if region_arg == "EU" :
            urls = groups.get_region_group_urlnames( EU_COUNTRIES )
        elif region_arg == "US" :
            urls = groups.get_region_group_urlnames( [ "USA" ] )
        else:
            urls = groups.get_region_group_urlnames()
            
        return urls
                    
    def batchMatch( self, collection ):
        agg = Agg( collection )
        agg.addMatch({ "batchID" : self._batchID } )
        return agg
    
    def matchGroup( self, urlname ):
        agg = Agg( self._mdb.pastEventsCollection())
        agg.addMatch({ "batchID"      : self._batchID, 
                       "event.status" : "past", 
                       "event.group.urlname" : urlname } )
        return agg
    
    def get_groups( self, urls, filename=None  ):
        '''
        Get all the groups listed by urls and their start dates
        '''
        
        agg = Agg( self._mdb.groupsCollection())
        agg.addMatch( { "batchID" : self._batchID,
                        "group.urlname" : { "$in" : urls }} )

        if self._pro_account:
            if self._start_date or self._end_date :
                agg.addRangeMatch( "group.founded_date", self._start_date, self._end_date )
            agg.addProject( { "_id" : 0,
                              "urlname" : "$group.urlname",
                              "members" : "$group.member_count",
                              "founded" : "$group.founded_date" } )
            print( "Using pro search" )
        else:
            if self._start_date or self._end_date :
                agg.addRangeMatch( "group.created", self._start_date, self._end_date )
            agg.addProject( { "_id" : 0,
                              "urlname" : "$group.urlname",
                              "members" : "$group.members",
                              "founded" : "$group.created" } ) 
            print( "Using nopro search")
        if self._sorter:
            agg.addSort( self._sorter)        
        
        if filename :
            self._filename = filename
            
        if self._view :
            agg.create_view( self._mdb.database(), "groups_view" )
            
        formatter = CursorFormatter( agg, self._filename, self._format )
        filename = formatter.output( fieldNames= [ "urlname", "members", "founded" ], datemap=[ "founded" ], limit=self._limit )
        
        if self._filename != "-":
            self._files.append( self._filename )
            
    def get_group_totals( self, urls, filename=None ):
        '''
        get the total number of RSVPs by group.
        '''
    
        agg = Agg( self._mdb.pastEventsCollection())
    
        agg.addMatch({ "batchID"             : self._batchID,
                       "event.status"        : "past",
                       "event.group.urlname" : { "$in" : urls }} )
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "event.time", self._start_date, self._end_date )
            
        agg.addGroup( { "_id" : { "urlname" : "$event.group.urlname", 
                                  "year"    : { "$year" : "$event.time"}},
                        "event_count" : { "$sum" : 1 },
                        "rsvp_count"  : { "$sum" : "$event.yes_rsvp_count" }})
        
        agg.addProject( { "_id" : 0,
                          "group"   : "$_id.urlname",
                          "year"    : "$_id.year",
                          "event_count" : 1,
                          "rsvp_count" : 1 } )
        
        if self._sorter:
            agg.addSort( self._sorter )
    
        if filename :
            self._filename = filename

            
        if self._view :
            agg.create_view( self._mdb.database(), "group_totals_view" )
            
        formatter = CursorFormatter( agg, self._filename, self._format )
        filename = formatter.output( fieldNames= [ "year", "group", "event_count", "rsvp_count"], limit=self._limit )
        
        if self._filename != "-":
            self._files.append( self._filename )
        
    def get_events(self, urls, when="past", filename=None):
        '''
        Get events when=past means past events. when="upcoming" means future events.
        '''
    
        agg = None
        
        if when == "past" : 
            agg = Agg( self._mdb.pastEventsCollection())

        elif when == "upcoming" :
            agg = Agg( self._mdb.upcomingEventsCollection())

        
        agg.addMatch({ "batchID"      : self._batchID,
                       "event.status" : when,
                       "event.group.urlname" : { "$in" : urls }} )
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "event.time", self._start_date, self._end_date )
            
        agg.addProject( { "_id": 0, 
                          "group"        : u"$event.group.urlname", 
                          "name"         : u"$event.name",
                          "rsvp_count"   : "$event.yes_rsvp_count",
                          "date"         :"$event.time" }) 
     
        if self._sorter:
            agg.addSort( self._sorter)
        
        if filename :
            self._filename = filename

            
        if self._view :
            agg.create_view( self._mdb.database(), "events_view" )
            
        formatter = CursorFormatter( agg, self._filename, self._format )
        filename = formatter.output( fieldNames= [ "group", "name", "rsvp_count", "date" ], datemap=[ "date"], limit=self._limit)

        if self._filename != "-":
            self._files.append( self._filename )
            
    def get_new_members( self, urls, filename=None ):
        '''
        Get all the members of all the groups (urls). Range is join_time.
        '''
        
        agg = Agg( self._mdb.proMembersCollection())

        agg.addMatch({ "batchID"            : self._batchID } )
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "member.join_time", self._start_date, self._end_date )
            
        agg.addUnwind( "$member.chapters" )
        agg.addMatch({ "member.chapters.urlname" : { "$in" : urls }} )
            
        agg.addProject( { "_id" : 0,
                          "group"     : "$member.chapters.urlname",
                          "name"      : "$member.member_name",
                          "join_date" : "$member.join_time" } )
        
        if self._sorter:
            agg.addSort( self._sorter)
            
        if filename :
            self._filename = filename

            
        if self._view :
            agg.create_view( self._mdb.database(), "new_members_view" )
            
        formatter = CursorFormatter( agg, self._filename, self._format )
        filename = formatter.output( fieldNames= [ "group", "name", "join_date" ], datemap=[ 'join_date'], limit=self._limit)
        
        if self._filename != "-":
            self._files.append( self._filename )
            
    def get_rsvps( self, urls, filename=None):   
        '''
        Lookup RSVPs by user. So for each user collect how many events they RSVPed to.
        '''
        agg = Agg( self._mdb.attendeesCollection())
        
        agg.addMatch({ "batchID"            : self._batchID,
                       "info.event.group.urlname" : { "$in" : urls }} )
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "info.event.time", self._start_date, self._end_date )
        
        agg.addProject( { "_id"        : 0,
                          "attendee"   : "$info.attendee.member.name", 
                          "group"      : "$info.event.group.urlname",
                          "event_name" : "$info.event.name" })
        
        agg.addGroup( { "_id" : {  "attendee": "$attendee", "group": "$group" },
                        "event_count" : { "$sum" : 1 }})
                        
        agg.addProject( { "_id" : 0,
                          "attendee" : "$_id.attendee",
                          "group" : "$_id.group",
                          "event_count" : 1 } )
        
        if self._sorter :
            agg.addSort( self._sorter)
        
        if filename :
            self._filename = filename

            
        if self._view :
            agg.create_view( self._mdb.database(), "rsvps_view" )
            
        formatter = CursorFormatter( agg, self._filename, self._format )
        filename = formatter.output( fieldNames= [ "attendee", "group", "event_count" ], limit=self._limit )

        if self._filename != "-":
            self._files.append( self._filename )
            
    def get_rsvp_by_event(self, urls, filename="rsvp_events"):
        
        agg = Agg( self._mdb.pastEventsCollection())
        
        agg.addMatch({ "batchID"             : self._batchID,
                       "event.group.urlname" : { "$in" : urls }})
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "event.time", self._start_date, self._end_date )
            
        agg.addGroup( { "_id" : "$event.group.urlname",
                        "rsvp_count" : { "$sum" : "$event.yes_rsvp_count" }})

        if self._sorter :
            agg.addSort( self._sorter)
            
        if filename :
            self._filename = filename
            
        if self._view :
            agg.create_view( self._mdb.database(), "rsvps_by_event_view" )
            
        formatter = CursorFormatter( agg.aggregate(), self._filename, self._format )
        filename = formatter.output( fieldNames= [ "_id", "rsvp_count" ], limit=self._limit )
        
        if self._filename != "-":
            self._files.append( self._filename )
        
    def get_active_users( self, urls, filename=None ):
        '''
        We define an active user as somebody who has rsvp'd to at least one event in the last six months.
        '''
        agg = Agg( self._mdb.attendeesCollection())
        
        agg.addMatch({ "batchID"            : self._batchID,
                       "info.event.group.urlname" : { "$in" : urls },
                       "info.attendee.rsvp.response" : "yes" } )
        
        if self._start_date or self._end_date :
            agg.addRangeMatch( "info.event.time", self._start_date, self._end_date )
        else:
            agg.addRangeMatch( "info.event.time", datetime.utcnow() + relativedelta(months=-6) )
        
    #     agg.addProject( { "_id" : 0,
    #                       "name" : "$info.attendee.member.name",
    #                       "urlname" : "$info.event.group.urlname",
    #                       "event_name" : "$info.event.name" })
    
        agg.addProject( { "_id" : 0,
                          "name" : "$info.attendee.member.name",
                          "event" : "$info.event.name",
                          "date" : "$info.event.time" } )
                         
        agg.addGroup( { "_id"    : "$name" ,
                        "count"  : { "$sum": 1 }} )
        
        if self._sorter :
            agg.addSort( self._sorter)
            
        if filename :
            self._filename = filename

            
        if self._view :
            agg.create_view( self._mdb.database(), "active_users_view" )
            
        formatter = CursorFormatter( agg, self._filename, self._format )
        filename = formatter.output( fieldNames= [ "_id", "count" ], limit=self._limit )

        if self._filename != "-":
            self._files.append( self._filename )
       
 
    def get_totals(self, urls, countries=None ):
        '''
        Total number of members
        Total number of groups
        Total number of events
        Total number of RSVPs
        '''
       
        members = Members( self._mdb )

        if countries is None:
            member_count = members.get_all_members().count()
        else:
            member_count = members.get_all_members( { "member.country" : { "$in" : countries }}).count()
        print( "Total members: %i" % member_count )
        
        events = PastEvents( self._mdb )
        
        event_count = events.get_all_events( { "event.group.urlname" : { "$in" : urls }}).count()
        
        print( "Total events: %i" % event_count )
    
        #group_count = groups.

    def output_filename(self):
        return self._filename
