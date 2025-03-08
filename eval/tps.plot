set term pdf size 8,3 enhanced color font "Times-New-Roman, 28"
set output 'tps.pdf'

set boxwidth 0.2
set style fill solid
set grid ytics
set ylabel 'TPS'
set xlabel 'S3 Upload Intervals (# of committed TXs)'

# Define the data
datafile = 'tps.dat'

# Set the data for the bars
set style data histogram
set style histogram clustered gap 1
set style fill solid border -1
set boxwidth 0.9

set key left top vertical reverse Left
set xtics scale 0
set xtics nomirror
set xrange [0.5:4.5]
set xtics ("1" 1, "100" 2, "500" 3, "1000" 4)
set yrange[0:45]
set ytics 0,10,45

set style fill pattern 1
set style fill pattern 2
set style fill pattern 3


plot datafile using 2:xtic(1) title 'Snapshot' fillstyle pattern 1 lc rgb '#666666', \
		 '' using 3 title 'Incremental' fillstyle pattern 2 lc rgb '#F0027F', \
		 '' using 4 title 'SSL-S3 (proposed)' fillstyle pattern 3 lc rgb '#386CB0'

