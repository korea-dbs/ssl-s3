set term pdf size 6,2 enhanced color font "Times-New-Roman, 20"
set output 'recv.pdf'

set style fill solid
set grid ytics
set ylabel 'Recovery Time (sec)'

# Define the data
datafile = 'recv.dat'

# Set the data for the bars
set style data histogram
set style histogram rowstacked
set style fill solid border -1
set boxwidth 0.5
set key right top vertical reverse Left invert
set xtics scale 0
set xtics nomirror
set yrange[0:85]
set ytics 0,20,80

set style fill pattern 1
set style fill pattern 2
set style fill pattern 3

plot datafile using 2:xtic(1) ti "S3 Fetch" fillstyle pattern 3 fc rgb "#F0027F" lt -1, \
		  '' using 3 ti "SQLite" fillstyle pattern 1 fc rgb "#386CB0" lt -1
