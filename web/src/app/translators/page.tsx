import { DataTable } from "@/components/data-table"

import data from "./data.json"

export default function Page() {
  return (
    <>
      <DataTable data={data} />
    </>
  )
}
