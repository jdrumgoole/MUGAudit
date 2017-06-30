'''
Created on 6 Sep 2016

@author: jdrumgoole
'''

import logging
import datetime

from copy import deepcopy

from mugalyser.version import __programName__
from mugalyser.meetup_request import MeetupRequest

def makeRequestURL( *args ):
    url = "https://api.meetup.com"
    
    for i in args:
        url = url + "/" + i
        
    return url

def epochToDatetime( ts ):
    return datetime.datetime.fromtimestamp( ts /1000 )

class Reshaper( object ):
    
    def __init__(self ):
        self._reshape = {}
        
    def add( self, key, value ):
        self._reshape[ key] = value
        
    @staticmethod
    def noop( d ):
        return d
 
    def reshape( self, doc ) :
        newDoc = doc.copy()
        newDoc.update( self._reshape )
        return newDoc

    @staticmethod
    def reshapeGeospatial( doc ):
        doc[ "location" ] = { "type" : "Point", "coordinates": [ doc["lon"], doc["lat" ]] }
        del doc[ 'lat']
        del doc[ 'lon']
        return doc

    @staticmethod
    def reshapeMemberDoc( doc ):
        return Reshaper.reshapeTime( Reshaper.reshapeGeospatial(doc), [ "joined", "join_time", "last_access_time" ])

    @staticmethod
    def reshapeEventDoc( doc ):
        return Reshaper.reshapeTime( doc, [ "created", "updated", "time" ])
    
    @staticmethod
    def reshapeTime( doc, keys ):
        for i in keys:
            if i in doc :
                doc[ i ] =epochToDatetime( doc[ i ])
        
        return doc
    
    @staticmethod
    def reshapeGroupDoc( doc ):
        return Reshaper.reshapeTime( Reshaper.reshapeGeospatial(doc), 
                                     [ "created", "pro_join_date", "founded_date", "last_event" ])
        
    
# def getHeaderLink( header ):
#     #print( "getHeaderLink( %s)" % header )
# 
#     if "," in header:
#         ( nxt, _ ) = header.split( ",", 2 )
#     else:
#         nxt = header
#         
#     ( link, relParam ) = nxt.split( ";", 2 )
#     ( _, relVal ) = relParam.split( "=", 2 )
#     link = link[1:-1] # strip angle brackets off link
#     relVal = relVal[ 1:-1] # strip off quotes
#     return ( link, relVal )


        
class MeetupAPI(object):
    '''
    classdocs
    '''

    
    def __init__(self, apikey, page=200):
        '''
        Constructor
        '''
        
        self._logger = logging.getLogger( __programName__)
        self._api = "https://api.meetup.com/"
        self._params = {}
        self._params[ "key" ] = apikey
        self._params[ "page" ] = page
        self._requester = MeetupRequest()
    
            
    def get_group(self, url_name ):
        
        return Reshaper.reshapeGroupDoc( self._requester.simple_request( self._api + url_name, params = self._params )[1] ) 

    def get_groups_by_url(self, urls ):
        for i in urls:
            yield self.get_group( i )
            
    def get_past_events(self, url_name ) :
        
        params = deepcopy( self._params )
        
        params[ "status" ]       = "past"
        params[ "group_urlname"] = url_name
        
        return self._requester.paged_request( self._api + "2/events", params )

    def get_all_attendees(self, groups=None ):
        groupsIterator = None
        if groups :
            groupsIterator = groups
        else:
            groupsIterator = self.get_groups()
            
        for group in groupsIterator :
            return self.get_attendees(group )
        
    def get_attendees( self, url_name ):
        
        for event in self.get_past_events( url_name ):
            #pprint( event )
            for attendee in self.get_event_attendees(event[ "id"], url_name ):
                yield ( attendee, event )
    
            
    def get_event_attendees(self, eventID, url_name ):
        
        #https://api.meetup.com/DublinMUG/events/62760772/attendance?&sign=true&photo-host=public&page=20
        reqURL = makeRequestURL( url_name, "events", str( eventID ), "attendance")
        return self._requester.paged_request( reqURL, self._params )
    
    def get_upcoming_events(self, url_name ):
        
        params = deepcopy( self._params )
        params[ "status" ] = "upcoming"
        params[ "group_urlname"] = url_name
        
        return self._requester.paged_request( self._api + "2/events", params )
    
    def get_member_by_id(self, member_id ):

        ( _, body ) = self._requester.simple_request( self._api + "2/member/" + str( member_id ), params = self._params )
        
        return body
    
    def get_members(self , urls ):
        for i in urls:
            for member in self.__get_members( i ):
                yield member
                
    def __get_members(self, url_name ):
        
        params = deepcopy( self._params )
        params[ "group_urlname" ] = url_name
 
        return self._requester.paged_request( self._api + "2/members", params )
    
    def get_groups(self ):
        '''
        Get all groups associated with this API key.
        '''
        self._logger.debug( "get_groups")
        return self._requester.paged_request(self._api + "self/groups",  self._params )
    
    def get_pro_groups(self  ):
        '''
        Get all groups associated with this API key.
        '''
        self._logger.debug( "get_pro_groups")
        
        return self._requester.paged_request( self._api + "pro/MongoDB/groups", self._params )
    
    def get_pro_group_names( self ):
        for i in self.get_pro_groups() :
            yield i[ "urlname" ]
            
    def get_pro_members(self ):
        
        self._logger.debug( "get_pro_members")
        #print( self._params )
        return self._requester.paged_request( self._api + "pro/MongoDB/members", self._params )

    