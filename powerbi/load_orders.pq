// Create a text parameter ExportFolder, e.g. C:\Projects\orderpulse\results\exports
let
    Source = Csv.Document(File.Contents(ExportFolder & "\fact_orders.csv"), [Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    Typed = Table.TransformColumnTypes(Headers, {{"order_id", type text}, {"customer_id", type text}, {"merchandise_brl", Currency.Type}, {"paid_brl", Currency.Type}, {"purchased_at", type datetime}, {"is_late", type logical}}),
    PurchaseDate = Table.AddColumn(Typed, "purchase_date", each Date.From([purchased_at]), type date)
in PurchaseDate
