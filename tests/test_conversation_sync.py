from app.services.pancake_api import ConversationSyncService

class FakeApi:
    def __init__(self): self.calls=[]
    def list_conversations(self, cursor=None):
        self.calls.append(cursor)
        return ({"data":[{"id":"1"},{"id":"1"}]+([{"id":"2"}]*59 if cursor is None else []), "last_conversation_id":"next"} if cursor is None else {"data":[{"id":"3"}]})

def test_sync_paginates_and_deduplicates():
    api=FakeApi(); rows,cursor=ConversationSyncService(api,min_interval=0).sync(max_pages=5)
    assert [r['id'] for r in rows] == ['1','2','3']; assert api.calls == [None,'next']

def test_sync_stops_on_repeated_cursor():
    class Loop(FakeApi):
        def list_conversations(self,cursor=None): return {"data":[{"id":"1"}]*60,"last_conversation_id":"same"}
    rows,_=ConversationSyncService(Loop(),min_interval=0).sync(max_pages=10)
    assert len(rows)==1
