#!/usr/bin/env perl
#
# Please read all the comments down to the line that says "TOP".
# These comments are divided into three sections:
#
#     1. usage instructions
#     2. installation instructions
#     3. standard copyright
#
# Feel free to share this script with other instructors of programming
# classes, but please do not place the script in a publicly accessible
# place.  Comments, questions, and bug reports should be sent to
# moss-request@moss.stanford.edu.
#
# IMPORTANT: This script is known to work on Unix and on Windows using Cygwin.
# It is not known to work on other ways of using Perl under Windows.  If the
# script does not work for you under Windows, you can try the email-based
# version for Windows (available on the Moss home page).
#

#
#  Section 1. Usage instructions
#
#  moss [-l language] [-d] [-b basefile1] ... [-b basefilen] [-m #] [-c "string"] file1 file2 file3 ...
#
# The -l option specifies the source language of the tested programs.
# Moss supports many different languages; see the variable "languages" below for the
# full list.
#
# Example: Compare the lisp programs foo.lisp and bar.lisp:
#
#    moss -l lisp foo.lisp bar.lisp
#
#
# The -d option specifies that submissions are by directory, not by file.
# That is, files in a directory are taken to be part of the same program,
# and reported matches are organized accordingly by directory.
#
# Example: Compare the programs foo and bar, which consist of .c and .h
# files in the directories foo and bar respectively.
#
#    moss -d foo/*.c foo/*.h bar/*.c bar/*.h
#
# Example: Each program consists of the *.c and *.h files in a directory under
# the directory "assignment1."
#
#    moss -d assignment1/*/*.h assignment1/*/*.c
#
#
# The -b option names a "base file".  Moss normally reports all code
# that matches in pairs of files.  When a base file is supplied,
# program code that also appears in the base file is not counted in matches.
# A typical base file will include, for example, the instructor-supplied
# code for an assignment.  Multiple -b options are allowed.  You should
# use a base file if it is convenient; base files improve results, but
# are not usually necessary for obtaining useful information.
#
# IMPORTANT: Unlike previous versions of moss, the -b option *always*
# takes a single filename, even if the -d option is also used.
#
# Examples:
#
#  Submit all of the C++ files in the current directory, using skeleton.cc
#  as the base file:
#
#    moss -l cc -b skeleton.cc *.cc
#
#  Submit all of the ML programs in directories asn1.96/* and asn1.97/*, where
#  asn1.97/instructor/example.ml and asn1.96/instructor/example.ml contain the base files.
#
#    moss -l ml -b asn1.97/instructor/example.ml -b asn1.96/instructor/example.ml -d asn1.97/*/*.ml asn1.96/*/*.ml
#
# The -m option sets the maximum number of times a given passage may appear
# before it is ignored.  A passage of code that appears in many programs
# is probably legitimate sharing and not the result of plagiarism.  With -m N,
# any passage appearing in more than N programs is treated as if it appeared in
# a base file (i.e., it is never reported).  Option -m can be used to control
# moss' sensitivity.  With -m 2, moss reports only passages that appear
# in exactly two programs.  If one expects many very similar solutions
# (e.g., the short first assignments typical of introductory programming
# courses) then using -m 3 or -m 4 is a good way to eliminate all but
# truly unusual matches between programs while still being able to detect
# 3-way or 4-way plagiarism.  With -m 1000000 (or any very
# large number), moss reports all matches, no matter how often they appear.
# The -m setting is most useful for large assignments where one also a base file
# expected to hold all legitimately shared code.  The default for -m is 10.
#
# Examples:
#
#   moss -l pascal -m 2 *.pascal
#   moss -l cc -m 1000000 -b mycode.cc asn1/*.cc
#
#
# The -c option supplies a comment string that is attached to the generated
# report.  This option facilitates matching queries submitted with replies
# received, especially when several queries are submitted at once.
#
# Example:
#
#   moss -l scheme -c "Scheme programs" *.sch
#
# The -n option determines the number of matching files to show in the results.
# The default is 250.
#
# Example:
#   moss -c java -n 200 *.java
# The -x option sends queries to the current experimental version of the server.
# The experimental server has the most recent Moss features and is also usually
# less stable (read: may have more bugs).
#
# Example:
#
#   moss -x -l ml *.ml
#


#
# Section 2.  Installation instructions.
#
# You may need to change the very first line of this script
# if perl is not in /usr/bin on your system.  Just replace /usr/bin
# with the pathname of the directory where perl resides.
#

#
#  3. Standard Copyright
#
#Copyright (c) 1997 The Regents of the University of California.
#All rights reserved.
#
#Permission to use, copy, modify, and distribute this software for any
#purpose, without fee, and without written agreement is hereby granted,
#provided that the above copyright notice and the following two
#paragraphs appear in all copies of this software.
#
#IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE TO ANY PARTY FOR
#DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES ARISING OUT
#OF THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF THE UNIVERSITY OF
#CALIFORNIA HAS BEEN ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#
#THE UNIVERSITY OF CALIFORNIA SPECIFICALLY DISCLAIMS ANY WARRANTIES,
#INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY
#AND FITNESS FOR A PARTICULAR PURPOSE.  THE SOFTWARE PROVIDED HEREUNDER IS
#ON AN "AS IS" BASIS, AND THE UNIVERSITY OF CALIFORNIA HAS NO OBLIGATION TO
#PROVIDE MAINTENANCE, SUPPORT, UPDATES, ENHANCEMENTS, OR MODIFICATIONS.
#
#
# STOP.  It should not be necessary to change anything below this line
# to use the script.
#
use IO::Socket;

#
# As of the date this script was written, the following languages were supported.  This script will work with
# languages added later however.  Check the moss website for the full list of supported languages.
#
@languages = ("c", "cc", "java", "ml", "pascal", "ada", "lisp", "scheme", "haskell", "fortran", "ascii", "vhdl", "perl", "matlab", "python", "mips", "prolog", "spice", "vb", "csharp", "modula2", "a8086", "javascript", "plsql");

$server = 'moss.stanford.edu';
$port = '7690';
$noreq = "Request not sent.";
$usage = "usage: moss [-x] [-l language] [-d] [-b basefile1] ... [-b basefilen] [-m #] [-c \"string\"] file1 file2 file3 ...";

#
# The userid is used to authenticate your queries to the server; don't change it!
#
$userid=YOUR_USER_ID_HERE;

#
# Process the command line options.  This is done in a non-standard
# way to allow multiple -b's.
#
$opt_l = "c";   # default language is c
$opt_m = 10;
$opt_d = 0;
$opt_x = 0;
$opt_c = "";
$opt_n = 250;
$bindex = 0;    # this becomes non-zero if we have any base files

while (@ARGV && ($_ = $ARGV[0]) =~ /^-(.)(.*)/) {
    ($first,$rest) = ($1,$2);

    shift(@ARGV);
    if ($first eq "d") {
    $opt_d = 1;
    next;
    }
    if ($first eq "b") {
    if($rest eq '') {
        die "No argument for option -b.\n" unless @ARGV;
        $rest = shift(@ARGV);
    }
    $opt_b[$bindex++] = $rest;
    next;
    }
    if ($first eq "l") {
    if ($rest eq '') {
        die "No argument for option -l.\n" unless @ARGV;
        $rest = shift(@ARGV);
    }
    $opt_l = $rest;
    next;
    }
    if ($first eq "m") {
    if($rest eq '') {
        die "No argument for option -m.\n" unless @ARGV;
        $rest = shift(@ARGV);
    }
    $opt_m = $rest;
    next;
    }
    if ($first eq "c") {
    if($rest eq '') {
        die "No argument for option -c.\n" unless @ARGV;
        $rest = shift(@ARGV);
    }
    $opt_c = $rest;
    next;
    }
    if ($first eq "n") {
    if($rest eq '') {
        die "No argument for option -n.\n" unless @ARGV;
        $rest = shift(@ARGV);
    }
    $opt_n = $rest;
    next;
    }
    if ($first eq "x") {
    $opt_x = 1;
    next;
    }
    #
    # Override the name of the server.  This is used for testing this script.
    #
    if ($first eq "s") {
    $server = shift(@ARGV);
    next;
    }
    #
    # Override the port.  This is used for testing this script.
    #
    if ($first eq "p") {
    $port = shift(@ARGV);
    next;
    }
    die "Unrecognized option -$first.  $usage\n";
}

#
# Check a bunch of things first to ensure that the
# script will be able to run to completion.
#

#
# Make sure all the argument files exist and are readable.
#
print "Checking files . . . \n";
$i = 0;
while($i < $bindex)
{
    die "Base file $opt_b[$i] does not exist. $noreq\n" unless -e "$opt_b[$i]";
    die "Base file $opt_b[$i] is not readable. $noreq\n" unless -r "$opt_b[$i]";
    die "Base file $opt_b is not a text file. $noreq\n" unless -T "$opt_b[$i]";
    $i++;
}
foreach $file (@ARGV)
{
    die "File $file does not exist. $noreq\n" unless -e "$file";
    die "File $file is not readable. $noreq\n" unless -r "$file";
    die "File $file is not a text file. $noreq\n" unless -T "$file";
}

if ("@ARGV" eq '') {
    die "No files submitted.\n $usage";
}
print "OK\n";

#
# Now the real processing begins.
#


$sock = new IO::Socket::INET (
                                  PeerAddr => $server,
                                  PeerPort => $port,
                                  Proto => 'tcp',
                                 );
die "Could not connect to server $server: $!\n" unless $sock;
$sock->autoflush(1);

sub read_from_server {
    $msg = <$sock>;
    print $msg;
}

sub upload_file {
    local ($file, $id, $lang) = @_;
#
# The stat function does not seem to give correct filesizes on windows, so
# we compute the size here via brute force.
#
    open(F,$file);
    $size = 0;
    while (<F>) {
    $size += length($_);
    }
    close(F);

    #  OK Customization to avoid long output
    #  Used to be a print here.
    print $sock "file $id $lang $size $file\n";
    open(F,$file);
    while (<F>) {
    print $sock $_;
    }
    close(F);
    #  OK Customization to avoid long output
    #  Used to be a print here.
}


print $sock "moss $userid\n";      # authenticate user
print $sock "directory $opt_d\n";
print $sock "X $opt_x\n";
print $sock "maxmatches $opt_m\n";
print $sock "show $opt_n\n";

#
# confirm that we have a supported languages
#
print $sock "language $opt_l\n";
$msg = <$sock>;
chop($msg);
if ($msg eq "no") {
    print $sock "end\n";
    die "Unrecognized language $opt_l.";
}


# upload any base files
$i = 0;
while($i < $bindex) {
    &upload_file($opt_b[$i++],0,$opt_l);
}

$setid = 1;
foreach $file (@ARGV) {
    &upload_file($file,$setid++,$opt_l);
}

print $sock "query 0 $opt_c\n";
print "Query submitted.  Waiting for the server's response.\n";
&read_from_server();
print $sock "end\n";
close($sock);


