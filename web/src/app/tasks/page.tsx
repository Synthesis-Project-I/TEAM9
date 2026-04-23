import { DataTable } from "@/components/data-table"
import { type ColumnDef } from "@tanstack/react-table"
import React, { useState, useEffect } from 'react'

function DragHandle({ id }: { id: number }) {
  const { attributes, listeners } = useSortable({
    id,
  })

  return (
    <Button
      {...attributes}
      {...listeners}
      variant="ghost"
      size="icon"
      className="size-7 text-muted-foreground hover:bg-transparent"
    >
      <GripVerticalIcon className="size-3 text-muted-foreground" />
      <span className="sr-only">Drag to reorder</span>
    </Button>
  )
}

import {
  useSortable,
} from "@dnd-kit/sortable"
import {
  type ColumnDef,
} from "@tanstack/react-table"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Checkbox } from "@/components/ui/checkbox"
import { GripVerticalIcon } from "lucide-react"

type Task = {
  index: number
  PROJECT_ID: number
  PM: string
  TASK_ID: number
  START: string
  END: string
  TASK_TYPE: string
  SOURCE_LANG: string
  TARGET_LANG: string
  TRANSLATOR: string
  ASSIGNED: string
  READY: string
  WORKING: string
  DELIVERED: string
  RECEIVED: string
  CLOSE: string
  HOURS: number
  HOURLY_RATE: number
  COST: number
  QUALITY_EVALUATION: number
  MANUFACTURER: string
  MANUFACTURER_SECTOR: string
  MANUFACTURER_INDUSTRY_GROUP: string
  MANUFACTURER_INDUSTRY: string
  MANUFACTURER_SUBINDUSTRY: string
}

const columns: ColumnDef<Task>[] = [
  {
    id: "drag",
    header: () => null,
    cell: ({ row }) => <DragHandle id={row.original.index} />,
  },
  {
    id: "select",
    header: ({ table }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={
            table.getIsAllPageRowsSelected() ||
            (table.getIsSomePageRowsSelected() && "indeterminate")
          }
          onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
          aria-label="Select all"
        />
      </div>
    ),
    cell: ({ row }) => (
      <div className="flex items-center justify-center">
        <Checkbox
          checked={row.getIsSelected()}
          onCheckedChange={(value) => row.toggleSelected(!!value)}
          aria-label="Select row"
        />
      </div>
    ),
    enableSorting: false,
    enableHiding: false,
  },
  {
    accessorKey: "PROJECT_ID",
    header: "Project ID",
    cell: ({ row }) => (
      <h1>
        {row.original.PROJECT_ID}
      </h1>
    ),
  },
  {
    accessorKey: "PM",
    header: "PM",
    cell: ({ row }) => (
      <h1>
        {row.original.PM}
      </h1>
    ),
  },
  {
    accessorKey: "TASK_ID",
    header: "Task ID",
    cell: ({ row }) => (
      <h1>
        {row.original.TASK_ID}
      </h1>
    ),
  },  {
    accessorKey: "START",
    header: "Start",
    cell: ({ row }) => (
      <h1>
        {row.original.START}
      </h1>
    ),
  },  {
    accessorKey: "END",
    header: "End",
    cell: ({ row }) => (
      <h1>
        {row.original.END}
      </h1>
    ),
  },  {
    accessorKey: "TASK_TYPE",
    header: "Task Type",
    cell: ({ row }) => (
      <h1>
        {row.original.TASK_TYPE}
      </h1>
    ),
  },  {
    accessorKey: "TRANSLATOR",
    header: "Translator",
    cell: ({ row }) => (
      <h1>
        {row.original.TRANSLATOR}
      </h1>
    ),
  },  {
    accessorKey: "ASSIGNED",
    header: "Assigned",
    cell: ({ row }) => (
      <h1>
        {row.original.ASSIGNED}
      </h1>
    ),
  },  {
    accessorKey: "READY",
    header: "Ready",
    cell: ({ row }) => (
      <h1>
        {row.original.READY}
      </h1>
    ),
  },  {
    accessorKey: "WORKING",
    header: "Working",
    cell: ({ row }) => (
      <h1>
        {row.original.WORKING}
      </h1>
    ),
  },  {
    accessorKey: "DELIVERED",
    header: "Delivered",
    cell: ({ row }) => (
      <h1>
        {row.original.DELIVERED}
      </h1>
    ),
  },  {
    accessorKey: "RECEIVED",
    header: "Received",
    cell: ({ row }) => (
      <h1>
        {row.original.RECEIVED}
      </h1>
    ),
  },  {
    accessorKey: "CLOSE",
    header: "Close",
    cell: ({ row }) => (
      <h1>
        {row.original.CLOSE}
      </h1>
    ),
  },  {
    accessorKey: "HOURS",
    header: "Hours",
    cell: ({ row }) => (
      <h1>
        {row.original.HOURS}
      </h1>
    ),
  },  {
    accessorKey: "HOURLY_RATE",
    header: "Hourly Rate",
    cell: ({ row }) => (
      <h1>
        {row.original.HOURLY_RATE}
      </h1>
    ),
  },  {
    accessorKey: "COST",
    header: "Cost",
    cell: ({ row }) => (
      <h1>
        {row.original.COST}
      </h1>
    ),
  },  {
    accessorKey: "QUALITY_EVALUATION",
    header: "Quality Evaluation",
    cell: ({ row }) => (
      <h1>
        {row.original.QUALITY_EVALUATION}
      </h1>
    ),
  },  {
    accessorKey: "MANUFACTURER",
    header: "MANUFACTURER",
    cell: ({ row }) => (
      <h1>
        {row.original.MANUFACTURER}
      </h1>
    ),
  },  {
    accessorKey: "MANUFACTURER_SECTOR",
    header: "MANUFACTURER_SECTOR",
    cell: ({ row }) => (
      <h1>
        {row.original.MANUFACTURER_SECTOR}
      </h1>
    ),
  },  {
    accessorKey: "MANUFACTURER_INDUSTRY_GROUP",
    header: "MANUFACTURER_INDUSTRY_GROUP",
    cell: ({ row }) => (
      <h1>
        {row.original.MANUFACTURER_INDUSTRY_GROUP}
      </h1>
    ),
  },  {
    accessorKey: "MANUFACTURER_INDUSTRY",
    header: "MANUFACTURER_INDUSTRY",
    cell: ({ row }) => (
      <h1>
        {row.original.MANUFACTURER_INDUSTRY}
      </h1>
    ),
  },  {
    accessorKey: "MANUFACTURER_SUBINDUSTRY",
    header: "MANUFACTURER_SUBINDUSTRY",
    cell: ({ row }) => (
      <h1>
        {row.original.MANUFACTURER_SUBINDUSTRY}
      </h1>
    ),
  },
  {
    accessorKey: "SOURCE_LANG",
    header: "Source Language",
    cell: ({ row }) => (
      <div className="w-32">
        <Badge variant="outline" className="px-1.5 text-muted-foreground">
          {row.original.SOURCE_LANG}
        </Badge>
      </div>
    ),
  },  
  {
    accessorKey: "TARGET_LANG",
    header: "Target Language",
    cell: ({ row }) => (
      <div className="w-32">
        <Badge variant="outline" className="px-1.5 text-muted-foreground">
          {row.original.TARGET_LANG}
        </Badge>
      </div>
    ),
  }

  ]

export default function Page() {
  const [data, setData] = useState<Task[] | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const [pageSize, setPageSize] = useState(50)
  const [pageIndex, setPageIndex] = useState(1)
  const [pageCount, setPageCount] = useState(10)
  const [asc, setAsc] = useState(true)
  const [sortBy, setSortBy] = useState("TRANSLATOR")

  const fetchData = async (page: number, size: number) => {
    setLoading(true)
    try {
      const apiUrl = `http://casaalbertojuarez2.ddns.net:8000/tasks?per_page=${pageSize}&page=${pageIndex}&sort_by=${sortBy}&asc=${asc}`
      const response = await fetch(apiUrl)
      const result = await response.json()
      // console.log(response)
      // console.log(result)
      
      setData(result.data)
      setPageCount(result.total_pages)
    } catch (err) {
      console.error(err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData(pageIndex, pageSize)
  }, [pageIndex, pageSize])

  if (loading) return <div>Loading...</div>
  if (error) return <div>Error: {error}</div>

  return (
    <>
      <DataTable 
        data={data} 
        columns={columns} 
        enableDragAndDrop={false} 
        enableRowSelection={true} 
        pageCount={pageCount} 
        pageSize={pageSize} 
        pageIndex={pageIndex - 1} 
        onPaginationChange={(newPagination) => {
          setPageIndex(newPagination.pageIndex + 1)
          setPageSize(newPagination.pageSize)
        }} 
        manualPagination={true} 
      />
    </>
  )
}
