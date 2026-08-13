from app.tools.ticketing import TicketCreateArgs, handle


def test_creates_ticket_with_id():
    result = handle(TicketCreateArgs(title="Billing issue", description="Customer charged twice."))
    assert result["status"] == "created"
    assert result["ticket_id"].startswith("TKT-")
    assert result["priority"] == "normal"


def test_ticket_ids_are_unique():
    a = handle(TicketCreateArgs(title="A", description="a"))
    b = handle(TicketCreateArgs(title="B", description="b"))
    assert a["ticket_id"] != b["ticket_id"]
